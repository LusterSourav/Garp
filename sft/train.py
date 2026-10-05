"""1 SFT run (102_first_sft.py pattern). Needs TINKER_API_KEY +
tinker + tinker-cookbook installed; keep off Render, run once locally.
Usage: python3 sft/train.py pairs.jsonl [steps]
Burn: ~50 pairs x 2k tok x 15 steps on Qwen3.5-4B ≈ $2-4 of $10.
"""
import asyncio
import json
import sys

BASE_MODEL = "Qwen/Qwen3.5-4B"
RANK, LR, MAX_LEN = 16, 0.0002, 2048


async def main(pairs_path: str, steps: int) -> None:
    import tinker  # lazy: only exists where SDK installed
    from tinker_cookbook.renderers import (
        TrainOnWhat, conversation_to_datum, get_renderer)

    service = tinker.ServiceClient()
    tc = await service.create_lora_training_client_async(
        base_model=BASE_MODEL, rank=RANK)
    tok, renderer = tc.get_tokenizer(), get_renderer("qwen3_5",
                                                     tc.get_tokenizer())
    data = []
    with open(pairs_path) as f:
        for line in f:
            line = line.strip()
            if line:
                data.append(conversation_to_datum(
                    json.loads(line), renderer, max_length=MAX_LEN,
                    train_on_what=TrainOnWhat.LAST_ASSISTANT_MESSAGE))
    print(f"{len(data)} examples on {BASE_MODEL}")
    for s in range(steps):
        fw = await tc.forward_backward_async(data, "cross_entropy")
        op = await tc.optim_step_async(tinker.AdamParams(learning_rate=LR))
        await fw.result_async()
        await op.result_async()
        print(f"step {s} done")
    sc = await tc.save_weights_and_get_sampling_client_async()
    print("saved. sampling client ready:", type(sc).__name__)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1], int(sys.argv[2] if len(sys.argv) > 2 else 15)))
