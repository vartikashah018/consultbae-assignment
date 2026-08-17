from audio import get_audio_metadata

file_path = "uploads/test_audio.m4a"

metadata = get_audio_metadata(file_path)

print("\nAudio metadata:")
print("----------------")

for key, value in metadata.items():
    print(f"{key}: {value}")