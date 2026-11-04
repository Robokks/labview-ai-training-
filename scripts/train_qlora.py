#!/usr/bin/env python3
"""Opt-in CUDA QLoRA pilot. Not executed in CI; does not upload data/model weights.

Usage example (authorized cloud GPU):
 python scripts/train_qlora.py --train-jsonl approved/train.jsonl \
   --model Qwen/Qwen3-1.7B --output-dir output/qwen3-pilot

Requires pip install -e ".[cloud]" and compatible versions of torch/transformers/peft.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument("--train-jsonl",required=True,type=Path)
    p.add_argument("--model",default="Qwen/Qwen3-1.7B")
    p.add_argument("--output-dir",required=True,type=Path)
    p.add_argument("--max-length",type=int,default=2048)
    p.add_argument("--epochs",type=float,default=1.0)
    p.add_argument("--lr",type=float,default=2e-4)
    p.add_argument("--lora-rank",type=int,default=16)
    p.add_argument("--seed",type=int,default=42)
    args=p.parse_args()
    import torch
    if not torch.cuda.is_available():
        raise RuntimeError("Refusing cloud QLoRA without a CUDA GPU")
    from transformers import (
        AutoTokenizer,AutoModelForCausalLM,BitsAndBytesConfig,
        Trainer,TrainingArguments,
    )
    from peft import LoraConfig,TaskType,get_peft_model,prepare_model_for_kbit_training

    records=[]
    for line in args.train_jsonl.read_text(encoding="utf-8").splitlines():
        if line.strip():
            item=json.loads(line)
            msgs=item["messages"]
            if len(msgs)!=3 or msgs[2]["role"]!="assistant":
                raise ValueError("Expected system, user, assistant messages")
            records.append(msgs)
    if not records:
        raise ValueError("Approved training JSONL contains no samples")
    tokenizer=AutoTokenizer.from_pretrained(args.model,trust_remote_code=False)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token=tokenizer.eos_token
    samples=[]
    for msgs in records:
        prompt=tokenizer.apply_chat_template(
            msgs[:2],tokenize=False,add_generation_prompt=True)
        answer=msgs[2]["content"] + tokenizer.eos_token
        prompt_ids=tokenizer(prompt,add_special_tokens=False)["input_ids"]
        answer_ids=tokenizer(answer,add_special_tokens=False)["input_ids"]
        allowed=args.max_length-len(prompt_ids)
        if allowed<=0:
            continue
        answer_ids=answer_ids[:allowed]
        ids=prompt_ids+answer_ids
        samples.append({"input_ids":ids,"attention_mask":[1]*len(ids),
                        "labels":[-100]*len(prompt_ids)+answer_ids})
    if not samples:
        raise ValueError("No training answers fit the chosen max-length")

    quant=BitsAndBytesConfig(
        load_in_4bit=True,bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.bfloat16 if torch.cuda.is_bf16_supported()
                                else torch.float16)
    model=AutoModelForCausalLM.from_pretrained(
        args.model,quantization_config=quant,device_map={"":0},trust_remote_code=False)
    model=prepare_model_for_kbit_training(model)
    model=get_peft_model(model,LoraConfig(
        r=args.lora_rank,lora_alpha=args.lora_rank*2,lora_dropout=0.05,
        target_modules="all-linear",bias="none",task_type=TaskType.CAUSAL_LM))
    def collate(batch):
        maxlen=max(len(x["input_ids"]) for x in batch)
        ids=[x["input_ids"]+[tokenizer.pad_token_id]*(maxlen-len(x["input_ids"]))
             for x in batch]
        mask=[x["attention_mask"]+[0]*(maxlen-len(x["attention_mask"]))
              for x in batch]
        labels=[x["labels"]+[-100]*(maxlen-len(x["labels"])) for x in batch]
        return {"input_ids":torch.tensor(ids),"attention_mask":torch.tensor(mask),
                "labels":torch.tensor(labels)}
    args.output_dir.mkdir(parents=True,exist_ok=True)
    train_args=TrainingArguments(
        output_dir=str(args.output_dir),num_train_epochs=args.epochs,
        per_device_train_batch_size=1,gradient_accumulation_steps=8,
        learning_rate=args.lr,logging_steps=10,
        save_strategy="epoch",report_to="none",seed=args.seed,
        fp16=not torch.cuda.is_bf16_supported(),
        bf16=torch.cuda.is_bf16_supported(),
        gradient_checkpointing=True,push_to_hub=False)
    trainer=Trainer(model=model,args=train_args,train_dataset=samples,data_collator=collate)
    trainer.train()
    model.save_pretrained(args.output_dir/"adapter")
    tokenizer.save_pretrained(args.output_dir/"adapter")
    import transformers
    import peft
    manifest={
        "model":args.model,"train_sha256":file_hash(args.train_jsonl),
        "samples":len(samples),"epochs":args.epochs,"lora_rank":args.lora_rank,
        "max_length":args.max_length,"seed":args.seed,
        "gpu":torch.cuda.get_device_name(0),
        "torch":torch.__version__,"transformers":transformers.__version__,
        "peft":peft.__version__,"upload_performed":False}
    (args.output_dir/"run_manifest.json").write_text(
        json.dumps(manifest,indent=2),encoding="utf-8")
    print("Adapter saved locally in cloud workspace; no automatic upload.")
if __name__=="__main__":
    main()
