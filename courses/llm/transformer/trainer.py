import math
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from datasets import load_dataset
import spacy
from tqdm.auto import tqdm, trange
import time
import numpy as np
import sys
import time
from tqdm import tqdm  # 仅用于构建词汇表



# 超参数配置
class Config:
    # 模型参数
    d_model = 256
    n_heads = 3
    num_layers = 4
    d_ff = 2048
    dropout = 0.2
    d_k = d_v = d_model // n_heads

    # 训练参数
    batch_size = 64
    max_len = 40
    min_freq = 2
    lr = 5e-5
    epochs = 300
    num_workers = 0  # Windows下设为0


# 词汇表类
class Vocabulary:
    def __init__(self, tokenizer):
        self.word2idx = {"<pad>": 0, "<sos>": 1, "<eos>": 2, "<unk>": 3}
        self.idx2word = {v: k for k, v in self.word2idx.items()}
        self.tokenizer = tokenizer

    def build_vocab(self, sentences, min_freq=2):
        freq = {}
        for sent in tqdm(sentences, desc="Building vocabulary"):
            for word in self.tokenizer(sent):
                freq[word.text.lower()] = freq.get(word.text.lower(), 0) + 1

        for word, count in freq.items():
            if count >= min_freq and word not in self.word2idx:
                idx = len(self.word2idx)
                self.word2idx[word] = idx
                self.idx2word[idx] = word


# 数据集类
class TranslationDataset(Dataset):
    def __init__(self, data, de_vocab, en_vocab, max_len=20):
        self.data = data
        self.de_vocab = de_vocab
        self.en_vocab = en_vocab
        self.max_len = max_len

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        src = [self.de_vocab.word2idx.get(tok.text.lower(), 3)
               for tok in self.de_vocab.tokenizer(self.data[idx]["de"])]
        trg = [self.en_vocab.word2idx.get(tok.text.lower(), 3)
               for tok in self.en_vocab.tokenizer(self.data[idx]["en"])]

        src = src[:self.max_len - 2]
        trg = trg[:self.max_len - 2]

        return (
            torch.LongTensor([1] + src + [2]),
            torch.LongTensor([1] + trg + [2])
        )


# 全局collate函数
def collate_fn(batch):
    src_batch, trg_batch = zip(*batch)
    return (
        nn.utils.rnn.pad_sequence(src_batch, padding_value=0, batch_first=True),
        nn.utils.rnn.pad_sequence(trg_batch, padding_value=0, batch_first=True)
    )


# Transformer组件
class PositionalEncoding(nn.Module):
    def __init__(self, d_model, dropout=0.1, max_len=5000):
        super().__init__()
        self.dropout = nn.Dropout(p=dropout)
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0).transpose(0, 1)
        self.register_buffer('pe', pe)

    def forward(self, x):
        x = x + self.pe[:x.size(0), :]
        return self.dropout(x)


def get_attn_pad_mask(seq_q, seq_k):
    batch_size, len_q = seq_q.size()
    _, len_k = seq_k.size()
    pad_attn_mask = seq_k.data.eq(0).unsqueeze(1)
    return pad_attn_mask.expand(batch_size, len_q, len_k)


def get_attn_subsequence_mask(seq):
    attn_shape = [seq.size(0), seq.size(1), seq.size(1)]
    subsequence_mask = torch.triu(torch.ones(attn_shape), diagonal=1)
    return subsequence_mask


class ScaledDotProductAttention(nn.Module):
    def __init__(self):
        super().__init__()

    def forward(self, Q, K, V, attn_mask):
        scores = torch.matmul(Q, K.transpose(-1, -2)) / np.sqrt(Config.d_k)
        scores.masked_fill_(attn_mask, -1e9)
        attn = nn.Softmax(dim=-1)(scores)
        context = torch.matmul(attn, V)
        return context, attn


class MultiHeadAttention(nn.Module):
    def __init__(self):
        super().__init__()
        self.W_Q = nn.Linear(Config.d_model, Config.d_k * Config.n_heads)
        self.W_K = nn.Linear(Config.d_model, Config.d_k * Config.n_heads)
        self.W_V = nn.Linear(Config.d_model, Config.d_v * Config.n_heads)
        self.fc = nn.Linear(Config.n_heads * Config.d_v, Config.d_model)
        self.layer_norm = nn.LayerNorm(Config.d_model)

    def forward(self, input_Q, input_K, input_V, attn_mask):
        residual = input_Q
        batch_size = input_Q.size(0)

        Q = self.W_Q(input_Q).view(batch_size, -1, Config.n_heads, Config.d_k).transpose(1, 2)
        K = self.W_K(input_K).view(batch_size, -1, Config.n_heads, Config.d_k).transpose(1, 2)
        V = self.W_V(input_V).view(batch_size, -1, Config.n_heads, Config.d_v).transpose(1, 2)

        attn_mask = attn_mask.unsqueeze(1).repeat(1, Config.n_heads, 1, 1)

        context, attn = ScaledDotProductAttention()(Q, K, V, attn_mask)
        context = context.transpose(1, 2).reshape(batch_size, -1, Config.n_heads * Config.d_v)
        output = self.fc(context)
        return self.layer_norm(output + residual), attn


class PoswiseFeedForwardNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc = nn.Sequential(
            nn.Linear(Config.d_model, Config.d_ff),
            nn.ReLU(),
            nn.Linear(Config.d_ff, Config.d_model)
        )
        self.layer_norm = nn.LayerNorm(Config.d_model)

    def forward(self, inputs):
        residual = inputs
        output = self.fc(inputs)
        return self.layer_norm(output + residual)


class EncoderLayer(nn.Module):
    def __init__(self):
        super().__init__()
        self.enc_self_attn = MultiHeadAttention()
        self.pos_ffn = PoswiseFeedForwardNet()

    def forward(self, enc_inputs, enc_self_attn_mask):
        enc_outputs, attn = self.enc_self_attn(enc_inputs, enc_inputs, enc_inputs, enc_self_attn_mask)
        enc_outputs = self.pos_ffn(enc_outputs)
        return enc_outputs, attn


class DecoderLayer(nn.Module):
    def __init__(self):
        super().__init__()
        self.dec_self_attn = MultiHeadAttention()
        self.dec_enc_attn = MultiHeadAttention()
        self.pos_ffn = PoswiseFeedForwardNet()

    def forward(self, dec_inputs, enc_outputs, dec_self_attn_mask, dec_enc_attn_mask):
        dec_outputs, dec_self_attn = self.dec_self_attn(dec_inputs, dec_inputs, dec_inputs, dec_self_attn_mask)
        dec_outputs, dec_enc_attn = self.dec_enc_attn(dec_outputs, enc_outputs, enc_outputs, dec_enc_attn_mask)
        dec_outputs = self.pos_ffn(dec_outputs)
        return dec_outputs, dec_self_attn, dec_enc_attn


class Encoder(nn.Module):
    def __init__(self, src_vocab_size):
        super().__init__()
        self.src_emb = nn.Embedding(src_vocab_size, Config.d_model)
        self.pos_enc = PositionalEncoding(Config.d_model, Config.dropout)
        self.layers = nn.ModuleList([EncoderLayer() for _ in range(Config.num_layers)])

    def forward(self, enc_inputs):
        enc_outputs = self.src_emb(enc_inputs)
        enc_outputs = self.pos_enc(enc_outputs.transpose(0, 1)).transpose(0, 1)
        enc_self_attn_mask = get_attn_pad_mask(enc_inputs, enc_inputs)
        enc_self_attns = []
        for layer in self.layers:
            enc_outputs, enc_self_attn = layer(enc_outputs, enc_self_attn_mask)
            enc_self_attns.append(enc_self_attn)
        return enc_outputs, enc_self_attns


class Decoder(nn.Module):
    def __init__(self, tgt_vocab_size):
        super().__init__()
        self.tgt_emb = nn.Embedding(tgt_vocab_size, Config.d_model)
        self.pos_enc = PositionalEncoding(Config.d_model, Config.dropout)
        self.layers = nn.ModuleList([DecoderLayer() for _ in range(Config.num_layers)])

    def forward(self, dec_inputs, enc_inputs, enc_outputs):
        dec_outputs = self.tgt_emb(dec_inputs)
        dec_outputs = self.pos_enc(dec_outputs.transpose(0, 1)).transpose(0, 1)

        dec_self_attn_pad_mask = get_attn_pad_mask(dec_inputs, dec_inputs)
        dec_self_attn_sub_mask = get_attn_subsequence_mask(dec_inputs)
        dec_self_attn_mask = torch.gt((dec_self_attn_pad_mask + dec_self_attn_sub_mask), 0)

        dec_enc_attn_mask = get_attn_pad_mask(dec_inputs, enc_inputs)

        dec_self_attns = []
        dec_enc_attns = []
        for layer in self.layers:
            dec_outputs, dec_self_attn, dec_enc_attn = layer(
                dec_outputs, enc_outputs, dec_self_attn_mask, dec_enc_attn_mask)
            dec_self_attns.append(dec_self_attn)
            dec_enc_attns.append(dec_enc_attn)
        return dec_outputs, dec_self_attns, dec_enc_attns


class Transformer(nn.Module):
    def __init__(self, src_vocab_size, tgt_vocab_size):
        super().__init__()
        self.encoder = Encoder(src_vocab_size)
        self.decoder = Decoder(tgt_vocab_size)
        self.projection = nn.Linear(Config.d_model, tgt_vocab_size)

    def forward(self, src, tgt):
        enc_outputs, _ = self.encoder(src)
        dec_outputs, _, _ = self.decoder(tgt, src, enc_outputs)
        return self.projection(dec_outputs)

    def count_parameters(self):
        return sum(p.numel() for p in self.parameters() if p.requires_grad)


def calculate_accuracy(output, target):
    preds = output.argmax(dim=-1)
    non_pad_mask = target != 0
    correct = (preds == target) & non_pad_mask
    accuracy = correct.sum().item() / non_pad_mask.sum().item()
    return accuracy


def main():
    # 1. 初始化环境
    print("Initializing environment...")
    spacy_de = spacy.load("de_core_news_sm", disable=["parser", "ner"])
    spacy_en = spacy.load("en_core_web_sm", disable=["parser", "ner"])
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    # 2. 加载数据并构建词汇表
    print("\nLoading dataset and building vocabularies...")
    dataset = load_dataset("bentrevett/multi30k", split={
        "train": "train[:1000]",
        "validation": "validation[:100]",
        "test": "test[:100]"
    })

    de_vocab = Vocabulary(spacy_de)
    en_vocab = Vocabulary(spacy_en)
    de_vocab.build_vocab([ex["de"] for ex in dataset["train"]])
    en_vocab.build_vocab([ex["en"] for ex in dataset["train"]])

    # 3. 创建数据集
    print("\nCreating datasets...")
    train_dataset = TranslationDataset(
        data=dataset["train"],
        de_vocab=de_vocab,
        en_vocab=en_vocab,
        max_len=Config.max_len
    )
    valid_dataset = TranslationDataset(
        data=dataset["validation"],
        de_vocab=de_vocab,
        en_vocab=en_vocab,
        max_len=Config.max_len
    )

    # 4. 创建数据加载器
    train_loader = DataLoader(
        train_dataset,
        batch_size=Config.batch_size,
        shuffle=True,
        collate_fn=collate_fn,
        num_workers=Config.num_workers
    )
    valid_loader = DataLoader(
        valid_dataset,
        batch_size=Config.batch_size,
        collate_fn=collate_fn,
        num_workers=Config.num_workers
    )

    # 5. 初始化模型
    print("\nInitializing model...")
    model = Transformer(
        src_vocab_size=len(de_vocab.word2idx),
        tgt_vocab_size=len(en_vocab.word2idx)
    ).to(device)
    print(f"Model parameters: {model.count_parameters() / 1e6:.2f}M")

    # 6. 训练配置
    optimizer = optim.AdamW(model.parameters(), lr=Config.lr, weight_decay=0.01)
    criterion = nn.CrossEntropyLoss(ignore_index=0)




    # 7. 训练循环
    print("\nStarting training...")
    best_loss = float('inf')

    for epoch in range(Config.epochs):
        # ===== 训练阶段 =====
        model.train()
        epoch_start = time.time()
        total_loss = 0
        total_accuracy = 0

        print(f"\nEpoch {epoch + 1}/{Config.epochs}")
        print("----------------------------------------")

        batch_start = time.time()
        for batch_idx, (src, tgt) in enumerate(train_loader, 1):
            src, tgt = src.to(device), tgt.to(device)

            # 正向传播
            optimizer.zero_grad()
            output = model(src, tgt[:, :-1])
            loss = criterion(output.view(-1, output.size(-1)),
                             tgt[:, 1:].contiguous().view(-1))

            # 反向传播
            loss.backward()
            optimizer.step()

            # 计算指标
            accuracy = calculate_accuracy(output.view(-1, output.size(-1)),
                                          tgt[:, 1:].contiguous().view(-1))
            total_loss += loss.item()
            total_accuracy += accuracy

            # 打印进度（单行刷新）
            batch_time = time.time() - batch_start
            print(f"\rBatch {batch_idx:03d}/{len(train_loader):03d} | "
                  f"Loss: {loss.item():.4f} | Acc: {accuracy:.4f} | "
                  f"Time: {batch_time:.2f}s/batch", end="", flush=True)
            batch_start = time.time()

        # 计算epoch平均指标
        avg_loss = total_loss / len(train_loader)
        avg_acc = total_accuracy / len(train_loader)
        epoch_time = time.time() - epoch_start

        # ===== 验证阶段 =====
        model.eval()
        val_loss = 0
        val_accuracy = 0
        with torch.no_grad():
            for src, tgt in valid_loader:
                src, tgt = src.to(device), tgt.to(device)
                output = model(src, tgt[:, :-1])
                val_loss += criterion(output.view(-1, output.size(-1)),
                                      tgt[:, 1:].contiguous().view(-1)).item()
                val_accuracy += calculate_accuracy(output.view(-1, output.size(-1)),
                                                   tgt[:, 1:].contiguous().view(-1))

        avg_val_loss = val_loss / len(valid_loader)
        avg_val_acc = val_accuracy / len(valid_loader)

        # 打印epoch总结
        print(f"\nSummary: "
              f"Train Loss: {avg_loss:.4f} | Train Acc: {avg_acc:.4f} | "
              f"Val Loss: {avg_val_loss:.4f} | Val Acc: {avg_val_acc:.4f} | "
              f"Time: {epoch_time:.2f}s")

        # 保存最佳模型
        if avg_val_loss < best_loss:
            best_loss = avg_val_loss
            torch.save(model.state_dict(), "best_model.pth")
            print(f"New best model saved (Loss: {best_loss:.4f})")

        print("----------------------------------------")

    # 8. 测试翻译（保持不变）
    def translate(sentence):
        model.eval()
        tokens = [de_vocab.word2idx.get(tok.text.lower(), 3)
                  for tok in spacy_de.tokenizer(sentence)]
        src = torch.LongTensor([1] + tokens + [2]).unsqueeze(0).to(device)
        tgt = torch.LongTensor([[1]]).to(device)

        with torch.no_grad():
            enc_outputs, _ = model.encoder(src)
            for _ in range(Config.max_len):
                dec_outputs, _, _ = model.decoder(tgt, src, enc_outputs)
                prob = model.projection(dec_outputs[:, -1])
                next_word = prob.argmax(-1)
                tgt = torch.cat([tgt, next_word.unsqueeze(0)], dim=1)
                if next_word.item() == 2:  # <eos>
                    break

        translated = [en_vocab.idx2word[idx.item()] for idx in tgt[0][1:-1]]
        return ' '.join(translated)




    # 8. 测试翻译
    def translate(sentence):
        model.eval()
        tokens = [de_vocab.word2idx.get(tok.text.lower(), 3)
                  for tok in spacy_de.tokenizer(sentence)]
        src = torch.LongTensor([1] + tokens + [2]).unsqueeze(0).to(device)
        tgt = torch.LongTensor([[1]]).to(device)

        with torch.no_grad():
            enc_outputs, _ = model.encoder(src)
            for _ in range(Config.max_len):
                dec_outputs, _, _ = model.decoder(tgt, src, enc_outputs)
                prob = model.projection(dec_outputs[:, -1])
                next_word = prob.argmax(-1)
                tgt = torch.cat([tgt, next_word.unsqueeze(0)], dim=1)
                if next_word.item() == 2:  # <eos>
                    break

        translated = [en_vocab.idx2word[idx.item()] for idx in tgt[0][1:-1]]
        return ' '.join(translated)

    print("\nTranslation Examples:")
    test_sentences = [
        "Ein Mann läuft im Park.",
        "Zwei Kinder graben Löcher in die Erde.",
        "Der braune Hund trägt ein schwarzes Halsband."
    ]
    for sent in test_sentences:
        print(f"DE: {sent}")
        print(f"EN: {translate(sent)}\n")


if __name__ == '__main__':
    main()