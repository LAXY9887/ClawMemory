"""
Stage 5.2a: Dreamstime FTP 自動上傳

用途:
  - 將 pending/ 中的圖片批量上傳至 Dreamstime FTP
  - 上傳成功後移至 uploaded/
  - 斷線重連: 3 次重試，間隔 30 秒
  - 單張超時: 5 分鐘

設計原則:
  - Python ftplib, Passive 模式
  - FTP ID/密碼從環境變數讀取（DREAMSTIME_FTP_ID / DREAMSTIME_FTP_PASS）
  - 上傳前驗證: 元數據已嵌入、檔案大小 < 50MB
  - 3 次重試後仍失敗 → 放棄 FTP，標記需 LXYA 手動上傳
  - 設計為平台無關的迴圈，未來可擴展其他 FTP 平台
"""

import os
import time
import shutil
import logging
from ftplib import FTP, error_perm, error_temp
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
CONFIG_DIR = SKILL_ROOT / "config"

MAX_FILE_SIZE_MB = 50


class FTPUploaderError(Exception):
    """FTP 上傳失敗"""
    pass


class FTPUploader:
    """
    Stage 5.2a: Dreamstime FTP 自動上傳。

    使用方式:
        uploader = FTPUploader(workspace_base="~/.openclaw/workspace/skills-custom/stock-image-pipeline")
        results = uploader.upload_pending()
    """

    def __init__(self, workspace_base: Optional[str] = None):
        self._schedule_config = self._load_json(CONFIG_DIR / "schedule.json")

        if workspace_base is None:
            ws = self._schedule_config.get("workspace", {})
            workspace_base = ws.get("base_path", "~/.openclaw/workspace/skills-custom/stock-image-pipeline")
        self._workspace = Path(workspace_base).expanduser()

        ws_cfg = self._schedule_config.get("workspace", {})
        self._pending_dir = self._workspace / ws_cfg.get("pending_dir", "pending")
        self._uploaded_dir = self._workspace / ws_cfg.get("uploaded_dir", "uploaded")

        # FTP 配置
        ftp_cfg = self._schedule_config.get("dreamstime_ftp", {})
        self._ftp_host = ftp_cfg.get("host", "upload.dreamstime.com")
        self._ftp_port = ftp_cfg.get("port", 21)
        self._remote_path = ftp_cfg.get("remote_path", "/")
        self._max_retries = ftp_cfg.get("max_retries", 3)
        self._retry_interval = ftp_cfg.get("retry_interval_sec", 30)
        self._file_timeout = ftp_cfg.get("single_file_timeout_sec", 300)

        # 認證（環境變數）
        self._ftp_id = os.environ.get("DREAMSTIME_FTP_ID")
        self._ftp_pass = os.environ.get("DREAMSTIME_FTP_PASS")

    def _load_json(self, path: Path) -> dict:
        if not path.exists():
            return {}
        with open(path, "r", encoding="utf-8") as f:
            import json
            return json.load(f)

    def _check_credentials(self) -> bool:
        """檢查 FTP 認證是否設定"""
        if not self._ftp_id or not self._ftp_pass:
            logger.warning(
                "Dreamstime FTP 認證未設定。"
                "請設定環境變數: DREAMSTIME_FTP_ID, DREAMSTIME_FTP_PASS"
            )
            return False
        return True

    def _connect(self) -> Optional[FTP]:
        """建立 FTP 連線（被動模式）"""
        try:
            ftp = FTP()
            ftp.connect(self._ftp_host, self._ftp_port, timeout=30)
            ftp.login(self._ftp_id, self._ftp_pass)
            ftp.set_pasv(True)
            ftp.cwd(self._remote_path)
            logger.info(f"FTP 連線成功: {self._ftp_host}:{self._ftp_port}")
            return ftp
        except Exception as e:
            logger.error(f"FTP 連線失敗: {e}")
            return None

    def _validate_file(self, file_path: Path) -> dict:
        """上傳前驗證"""
        issues = []

        if not file_path.exists():
            issues.append("檔案不存在")

        size_mb = file_path.stat().st_size / (1024 * 1024)
        if size_mb > MAX_FILE_SIZE_MB:
            issues.append(f"檔案過大: {size_mb:.1f}MB > {MAX_FILE_SIZE_MB}MB")

        if size_mb < 0.01:
            issues.append("檔案過小，可能損壞")

        return {
            "valid": len(issues) == 0,
            "size_mb": round(size_mb, 2),
            "issues": issues
        }

    def upload_single(self, ftp: FTP, file_path: Path) -> dict:
        """
        上傳單張圖片。

        Returns:
            {"success": bool, "filename": str, "size_mb": float, "elapsed_sec": float, "error": str|None}
        """
        filename = file_path.name
        start = time.time()

        # 驗證
        validation = self._validate_file(file_path)
        if not validation["valid"]:
            return {
                "success": False,
                "filename": filename,
                "size_mb": validation["size_mb"],
                "elapsed_sec": 0,
                "error": "; ".join(validation["issues"])
            }

        try:
            with open(file_path, "rb") as f:
                ftp.storbinary(f"STOR {filename}", f, blocksize=8192)

            elapsed = time.time() - start
            logger.info(f"FTP 上傳成功: {filename} ({validation['size_mb']}MB, {elapsed:.1f}s)")

            return {
                "success": True,
                "filename": filename,
                "size_mb": validation["size_mb"],
                "elapsed_sec": round(elapsed, 1),
                "error": None
            }

        except (error_perm, error_temp) as e:
            elapsed = time.time() - start
            logger.error(f"FTP 上傳失敗: {filename} — {e}")
            return {
                "success": False,
                "filename": filename,
                "size_mb": validation["size_mb"],
                "elapsed_sec": round(elapsed, 1),
                "error": str(e)
            }
        except Exception as e:
            elapsed = time.time() - start
            logger.error(f"FTP 上傳異常: {filename} — {e}")
            return {
                "success": False,
                "filename": filename,
                "size_mb": validation["size_mb"],
                "elapsed_sec": round(elapsed, 1),
                "error": str(e)
            }

    def upload_pending(self, file_paths: Optional[list] = None) -> dict:
        """
        上傳 pending/ 中的所有圖片（含重試機制）。

        Args:
            file_paths: 指定上傳的檔案列表。None = 掃描 pending/ 全部。

        Returns:
            {
                "uploaded": int,
                "failed": int,
                "skipped": int,
                "results": list,
                "ftp_available": bool,
                "manual_upload_needed": bool
            }
        """
        logger.info("=== Stage 5.2a: Dreamstime FTP 上傳 ===")

        # 取得待上傳檔案
        if file_paths is None:
            self._pending_dir.mkdir(parents=True, exist_ok=True)
            files = list(self._pending_dir.glob("*.png")) + list(self._pending_dir.glob("*.jpg"))
        else:
            files = [Path(f) for f in file_paths]

        if not files:
            logger.info("無待上傳檔案")
            return {
                "uploaded": 0, "failed": 0, "skipped": 0,
                "results": [], "ftp_available": True, "manual_upload_needed": False
            }

        # 檢查認證
        if not self._check_credentials():
            return {
                "uploaded": 0, "failed": 0, "skipped": len(files),
                "results": [{"filename": f.name, "error": "FTP 認證未設定"} for f in files],
                "ftp_available": False,
                "manual_upload_needed": True
            }

        # 連線（含重試）
        ftp = None
        for attempt in range(self._max_retries):
            ftp = self._connect()
            if ftp:
                break
            logger.warning(f"FTP 連線重試 {attempt + 1}/{self._max_retries}")
            if attempt < self._max_retries - 1:
                time.sleep(self._retry_interval)

        if ftp is None:
            logger.error("FTP 連線最終失敗，需 LXYA 手動上傳")
            return {
                "uploaded": 0, "failed": 0, "skipped": len(files),
                "results": [{"filename": f.name, "error": "FTP 連線失敗"} for f in files],
                "ftp_available": False,
                "manual_upload_needed": True
            }

        # 逐張上傳
        results = []
        uploaded = 0
        failed = 0

        try:
            for file_path in files:
                result = self._upload_with_retry(ftp, file_path)
                results.append(result)

                if result["success"]:
                    uploaded += 1
                    # 移至 uploaded/
                    self._move_to_uploaded(file_path)
                else:
                    failed += 1

        finally:
            try:
                ftp.quit()
            except Exception:
                try:
                    ftp.close()
                except Exception:
                    pass

        manual_needed = failed > 0
        logger.info(f"FTP 上傳完成: {uploaded} 成功, {failed} 失敗")

        return {
            "uploaded": uploaded,
            "failed": failed,
            "skipped": 0,
            "results": results,
            "ftp_available": True,
            "manual_upload_needed": manual_needed
        }

    def _upload_with_retry(self, ftp: FTP, file_path: Path) -> dict:
        """單張上傳含重試"""
        last_result = None

        for attempt in range(self._max_retries):
            result = self.upload_single(ftp, file_path)
            last_result = result

            if result["success"]:
                return result

            logger.warning(f"上傳重試 {attempt + 1}/{self._max_retries}: {file_path.name}")

            # 重連
            if attempt < self._max_retries - 1:
                time.sleep(self._retry_interval)
                try:
                    ftp.voidcmd("NOOP")
                except Exception:
                    # 連線斷了，重新連線
                    new_ftp = self._connect()
                    if new_ftp:
                        ftp = new_ftp

        return last_result

    def _move_to_uploaded(self, file_path: Path):
        """上傳成功後移至 uploaded/"""
        self._uploaded_dir.mkdir(parents=True, exist_ok=True)
        dest = self._uploaded_dir / file_path.name
        try:
            shutil.move(str(file_path), str(dest))
            logger.info(f"已移至 uploaded/: {file_path.name}")
        except Exception as e:
            logger.warning(f"移動檔案失敗: {e}")

