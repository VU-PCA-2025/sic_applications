from os.path import abspath, join

from sic_framework.devices.desktop import Desktop
from sic_framework.services.nlu.bert_nlu import (
    NLU,
    InferenceRequest,
    InferenceResult,
    NLUConf,
)
from sic_framework.services.openai_whisper_speech_to_text.whisper_speech_to_text import (
    GetTranscript,
    SICWhisper,
)



"""
This demo shows how to create a simple pipeline (ASR + NLU) where Whisper transcribes your speech and
feeds it into the NLU component to run inference

IMPORTANT
The Whisper component and NLU component need to be running:

1. Install dependencies:
    pip install social-interaction-cloud[whisper-speech-to-text,nlu]
2. Run the components:
    One terminal: run-whisper
    The other terminal: run-nlu
"""


desktop = Desktop()

whisper = SICWhisper()

# llm = SICLlm()

whisper.connect(desktop.mic)

ontology_path = abspath(join("..", "..", "conf", "nlu", "ontology.json"))
model_path = abspath(join("..", "..", "conf", "nlu", "model_checkpoint.pt"))
nlu_conf = NLUConf(ontology_path=ontology_path, model_path=model_path)
nlu = NLU(conf=nlu_conf)
print("Initiated NLU component!")


for i in range(10):
    print("..."*10, f"Talk now Round {i}")
    transcript = whisper.request(GetTranscript(timeout=10, phrase_time_limit=30))
    # Feed the whisper transcript to the NLU model to run inference
    nlu_result = nlu.request(InferenceRequest(transcript.transcript))
    # Feed the NLU result to the LLM model to run inference
    # query = f"transcript: {transcript.transcript}\n intent: {nlu_result.intent}\n slots: {nlu_result.slots}"
    # llm_result = llm.request(PromptRequest(query))

    kv_slots = {}
    for i, slot in enumerate(nlu_result.slots):
        if slot!='O':
            kv_slots[f"{slot}"] = transcript.transcript.split()[i]
    print("*"*10, "Here is the prediction!"*"*10")
    print("Transcript:", transcript.transcript)
    print("Intent:", nlu_result.intent)
    print("Slots:\n", kv_slots)
    print(nlu_result.intent_confidences)
    print("-"*20)
    # print(nlu_result.slot_confidences)
    # print("The LLM response is:", llm_result.response)

print("done")
