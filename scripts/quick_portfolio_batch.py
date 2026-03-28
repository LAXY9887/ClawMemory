#!/usr/bin/env python3
"""
快速批量生成 ClawClaw Spring 作品集
"""

import subprocess
import time
import concurrent.futures
import random

prompts_batch = [
    "ClawClaw with tech gadgets, spring workshop scene, inventor mood",
    "ClawClaw jumping over spring stream, dynamic action, water splash",
    "ClawClaw with butterfly on nose, cross-eyed cute expression, spring garden",
    "ClawClaw building flower crown, concentrated expression, craft scene",
    "ClawClaw on mountain top, spring landscape view, achievement pose",
    "ClawClaw with spring cleaning tools, organized workspace, productivity",
    "ClawClaw in hammock between trees, relaxing, spring afternoon nap",
    "ClawClaw with camera, photographing spring flowers, artist mood",
    "ClawClaw cooking outdoor meal, spring picnic preparation, chef outfit",
    "ClawClaw with backpack, hiking trail, spring adventure ready",
    "ClawClaw meditation pose, zen garden, spring tranquility",
    "ClawClaw with telescope, stargazing in spring evening, curious",
    "ClawClaw playing guitar under tree, musical spring scene",
    "ClawClaw with art supplies, painting spring landscape, creative",
    "ClawClaw racing paper boat in stream, playful spring activity",
    "ClawClaw with spring vegetables, healthy lifestyle, garden harvest",
    "ClawClaw doing yoga, morning spring routine, peaceful energy",
    "ClawClaw with kite, windy spring day, joyful play",
    "ClawClaw reading map, spring expedition planning, explorer mood",
    "ClawClaw with binoculars, bird watching, spring nature study"
]

def generate_single(prompt, index):
    """生成單張圖片"""
    try:
        cmd = f'cd skills/comfyui-skill-openclaw && .venv\\Scripts\\activate && python scripts/smart_generate.py -i "{prompt}" --model rinIllusionRNSFW_v20.safetensors'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=90)
        return f"✅ {index+1}: {prompt[:30]}..."
    except:
        return f"❌ {index+1}: {prompt[:30]}..."

def main():
    print("🚀 開始快速批量生成...")
    
    # 使用線程池併發生成
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(generate_single, prompt, i) for i, prompt in enumerate(prompts_batch)]
        
        for future in concurrent.futures.as_completed(futures):
            print(future.result())
            time.sleep(1)  # 避免過載
    
    print("🎉 批量生成完成！")

if __name__ == "__main__":
    main()