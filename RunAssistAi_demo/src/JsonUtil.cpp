// JsonUtil.cpp - robust JSON extraction & balancing
#include <string>
#include <algorithm>

namespace jsonutil {

static inline std::string trim(std::string s) {
    auto issp = [](unsigned char c){ return c==' '||c=='\t'||c=='\r'||c=='\n'; };
    s.erase(s.begin(), std::find_if(s.begin(), s.end(), [&](char c){ return !issp((unsigned char)c); }));
    s.erase(std::find_if(s.rbegin(), s.rend(), [&](char c){ return !issp((unsigned char)c); }).base(), s.end());
    return s;
}

static inline void strip_bom(std::string& s) {
    if (s.size() >= 3 && (unsigned char)s[0]==0xEF && (unsigned char)s[1]==0xBB && (unsigned char)s[2]==0xBF) {
        s.erase(0,3);
    }
}

static inline void strip_code_fences(std::string& s) {
    // remove ```...```; keep inner content
    size_t a = s.find("```");
    size_t b = s.rfind("```");
    if (a != std::string::npos && b != std::string::npos && b > a) {
        s = s.substr(a+3, b-(a+3));
    }
}

static std::string balance_json_like(std::string s) {
    // track {}, [] ignoring strings (simple heuristic)
    int curly = 0, square = 0;
    bool in_str = false, esc = false;

    for (char c : s) {
        if (in_str) {
            if (esc) { esc = false; continue; }
            if (c == '\\') { esc = true; continue; }
            if (c == '"') in_str = false;
            continue;
        }
        if (c == '"') { in_str = true; continue; }
        if (c == '{') ++curly;
        else if (c == '}') { if (curly>0) --curly; }
        else if (c == '[') ++square;
        else if (c == ']') { if (square>0) --square; }
    }
    // append missing closers in correct order: close arrays first if they are open at tail
    std::string tail;
    while (square-- > 0) tail += ']';
    while (curly--  > 0) tail += '}';
    s += tail;
    return s;
}

// Extract first `{...}` and auto-balance if truncated
std::string extractFirstJson(const std::string& raw) {
    std::string t = raw;
    strip_bom(t);
    strip_code_fences(t);
    t = trim(t);

    size_t s = t.find('{');
    if (s == std::string::npos) return "{}";

    // cut from first '{' to the best stopping point: first '}\n' or end
    size_t e = t.find("\n}\n", s);
    if (e != std::string::npos) {
        std::string cand = t.substr(s, e - s + 2);
        return trim(balance_json_like(cand));
    }
    // otherwise take until last } or whole remainder
    size_t last = t.find_last_of('}');
    std::string cand = (last != std::string::npos && last > s) ? t.substr(s, last - s + 1) : t.substr(s);
    // remove trailing ",}" / ",]" patterns
    auto fix_trailing_commas = [](std::string& x){
        for (;;) {
            bool changed = false;
            for (size_t p=0; (p = x.find(",}")) != std::string::npos; ) { x.erase(p,1); changed = true; }
            for (size_t p=0; (p = x.find(",]")) != std::string::npos; ) { x.erase(p,1); changed = true; }
            if (!changed) break;
        }
    };
    fix_trailing_commas(cand);
    return trim(balance_json_like(cand));
}

bool looksLikeJson(const std::string& s) {
    if (s.size() < 2) return false;
    size_t l = s.find_first_not_of(" \t\r\n");
    size_t r = s.find_last_not_of(" \t\r\n");
    return l != std::string::npos && r != std::string::npos && s[l]=='{' && s[r]=='}';
}

} // namespace jsonutil
