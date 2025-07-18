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

#speaker =interface.create_speaker("speak.wav")
#interface.save_speaker(speaker, "speak.json")
#speaker =interface.create_speaker("shout.wav")
#interface.save_speaker(speaker, "shout.json")
#speaker =interface.create_speaker("summary.wav")
#interface.save_speaker(speaker, "summary.json")

speaker = interface.load_speaker("speak.json")

output = interface.generate(
    config=outetts.GenerationConfig(
        text="Welcome folks, glad you could make it. Next round starts in 5 seconds!",
        speaker=speaker,
        #generation_type=outetts.GenerationType.GUIDED_WORDS,
    )
)

output.save("output.wav")

data, samplerate = sf.read("output.wav")
with io.BytesIO() as buf:
    sf.write(buf, data, samplerate, format='WAV')
    wav_bytes = buf.getvalue()

play(wav_bytes)
