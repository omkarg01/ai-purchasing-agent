import subprocess
import os

def create_master_soundtrack():
    audio_dir = os.path.abspath("scripts/demo/audio")
    
    # 0.8s silence audio
    silence_file = os.path.join(audio_dir, "silence_08s.mp3")
    subprocess.check_call([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
        "-t", "0.8", "-q:a", "9", silence_file
    ])
    
    # Concat list
    concat_list = os.path.join(audio_dir, "concat_list.txt")
    with open(concat_list, "w") as f:
        for i in range(1, 6):
            scene_name = f"scene{i}_"
            matched = [fn for fn in os.listdir(audio_dir) if fn.startswith(scene_name) and fn.endswith(".mp3")]
            if matched:
                f.write(f"file '{os.path.join(audio_dir, matched[0]).replace(chr(92), '/')}'\n")
                if i < 5:
                    f.write(f"file '{silence_file.replace(chr(92), '/')}'\n")
                    
    master_audio = os.path.join(audio_dir, "full_narration.mp3")
    subprocess.check_call([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
        "-c", "copy", master_audio
    ])
    
    dur = float(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", master_audio
    ]).decode().strip())
    
    print(f"Master soundtrack created: {master_audio}")
    print(f"Total Master Audio Duration: {dur:.2f}s ({dur/60:.2f} minutes)")
    return master_audio, dur

if __name__ == "__main__":
    create_master_soundtrack()

