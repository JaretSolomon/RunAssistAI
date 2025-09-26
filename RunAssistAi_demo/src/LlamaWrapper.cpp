// LlamaWrapper.cpp
// Compatible with your llama.h variant:
//  - tokenize: llama_tokenize(const llama_vocab*, const char*, int, llama_token*, int, bool, bool)
//  - vocab:    llama_model_get_vocab(model) -> const llama_vocab*
//  - piece:    llama_token_to_piece(vocab, token, buf, len, lstrip, special)  // 6 args
//  - decode:   llama_batch + llama_decode (manual fill), no llama_eval

#include "llama.h"
#include <string>
#include <vector>
#include <stdexcept>
#include <sstream>
#include <iostream>
#include <algorithm>

namespace lw {

static llama_model*         g_model = nullptr;
static llama_context*       g_ctx   = nullptr;
static const llama_vocab*   g_vocab = nullptr;

static int argmax(const float* logits, int n_vocab) {
    int best = 0; float v = logits[0];
    for (int i = 1; i < n_vocab; ++i) if (logits[i] > v) { v = logits[i]; best = i; }
    return best;
}

static std::string token_to_piece(llama_token tok) {
    char buf[512];
    int n = llama_token_to_piece(g_vocab, tok, buf, (int)sizeof(buf),
                                 /*lstrip*/ 0, /*special*/ true);
    if (n <= 0) return {};
    if (n < (int)sizeof(buf)) return std::string(buf, buf + n);
    std::string s; s.resize(n);
    llama_token_to_piece(g_vocab, tok, &s[0], n, /*lstrip*/ 0, /*special*/ true);
    return s;
}

bool init(const std::string& model_path, int n_ctx /*=2048*/, int n_gpu_layers /*=0*/) {
    if (g_ctx) return true;

    llama_backend_init();

    llama_model_params mp = llama_model_default_params();
    mp.n_gpu_layers = n_gpu_layers;   // 0 = CPU only
    mp.use_mmap     = true;
    mp.use_mlock    = false;

    g_model = llama_load_model_from_file(model_path.c_str(), mp);
    if (!g_model) {
        std::cerr << "load model failed: " << model_path << "\n";
        return false;
    }

    llama_context_params cp = llama_context_default_params();
    cp.n_ctx     = (n_ctx > 0 ? n_ctx : 2048);
    cp.n_threads = 0; 

    g_ctx = llama_new_context_with_model(g_model, cp);
    if (!g_ctx) {
        std::cerr << "new context failed\n";
        return false;
    }

    g_vocab = llama_model_get_vocab(g_model);
    if (!g_vocab) {
        std::cerr << "get vocab failed\n";
        return false;
    }
    return true;
}

std::string generate(const std::string& prompt, int max_tokens /*=512*/) {
    if (!g_ctx || !g_model || !g_vocab) throw std::runtime_error("llama not initialized");

    // 1) tokenize (C API)
    std::vector<llama_token> toks(prompt.size() + 8);
    int n_tok = llama_tokenize(
        g_vocab,
        prompt.c_str(),
        (int)prompt.size(),
        toks.data(),
        (int)toks.size(),
        /*add_special*/ true,
        /*parse_special*/ true
    );
    if (n_tok < 0) throw std::runtime_error("tokenize buffer too small");
    toks.resize(n_tok);
    const llama_token bos = llama_token_bos(g_vocab); 
    if (bos != -1) {
        toks.insert(toks.begin(), bos);
    }

    const int n_ctx_tokens = llama_n_ctx(g_ctx);
    if ((int)toks.size() >= n_ctx_tokens)
        throw std::runtime_error("prompt too long for context");

    // 2) build batch & feed prompt 
    llama_batch batch = llama_batch_init(std::max(n_ctx_tokens, 512), /*embd*/0, /*n_seq_max*/1);
    batch.n_tokens = 0;
    for (int i = 0; i < (int)toks.size(); ++i) {
        int idx = batch.n_tokens++;
        batch.token[idx]     = toks[i];
        batch.pos[idx]       = i;
        batch.n_seq_id[idx]  = 1;
        batch.seq_id[idx][0] = 0;
        batch.logits[idx]    = (i == (int)toks.size() - 1);
    }
    if (llama_decode(g_ctx, batch) != 0) {
        llama_batch_free(batch);
        throw std::runtime_error("llama_decode(prompt) failed");
    }

    // 3) generation loop (greedy)
    std::ostringstream out;
    const int n_vocab = llama_n_vocab(g_vocab);
    int n_past = (int)toks.size();

    for (int step = 0; step < max_tokens; ++step) {
        const float* logits = llama_get_logits(g_ctx);
        if (!logits) break;

        int tok = argmax(logits, n_vocab);
        if (tok == llama_token_eos(g_vocab)) break;

        out << token_to_piece(tok);

        batch.n_tokens = 0;
        int idx = batch.n_tokens++;
        batch.token[idx]     = tok;
        batch.pos[idx]       = n_past;
        batch.n_seq_id[idx]  = 1;
        batch.seq_id[idx][0] = 0;
        batch.logits[idx]    = 1; 

        if (llama_decode(g_ctx, batch) != 0) {
            llama_batch_free(batch);
            throw std::runtime_error("llama_decode(gen) failed");
        }
        ++n_past;
        if (n_past >= n_ctx_tokens - 1) break;
    }

    llama_batch_free(batch);
    return out.str();
}

void shutdown() {
    if (g_ctx)   { llama_free(g_ctx);   g_ctx   = nullptr; }
    if (g_model) { llama_free_model(g_model); g_model = nullptr; }
    g_vocab = nullptr;
    llama_backend_free();
}

} // namespace lw
