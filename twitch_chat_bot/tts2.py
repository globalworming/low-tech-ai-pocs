import outetts
import io
import soundfile as sf
from elevenlabs import play

interface = outetts.Interface(
    config=outetts.ModelConfig.auto_config(
            model=outetts.Models.VERSION_1_0_SIZE_1B,
            # For llama.cpp backend
            backend=outetts.Backend.LLAMACPP,
            quantization=outetts.LlamaCppQuantization.FP16
            # For transformers backend
            # backend=outetts.Backend.HF,
        )

)

speaker =interface.create_speaker("untitled.wav")
interface.save_speaker(speaker, "my_speaker.json")
speaker = interface.load_speaker("my_speaker.json")

output = interface.generate(
    config=outetts.GenerationConfig(
        text="Olivia Wins! The exploding sheep to the face was too much. See you all next time for the... WORMS RUMBLE!!!",
        speaker=speaker
    )
)

output.save("output.wav")

data, samplerate = sf.read("output.wav")
with io.BytesIO() as buf:
    sf.write(buf, data, samplerate, format='WAV')
    wav_bytes = buf.getvalue()

play(wav_bytes)
