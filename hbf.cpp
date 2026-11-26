// hbf.cpp — «Святой Брейнфак» (Holy Brainfuck, HBF) — интерпретатор на C++.
// 16 команд — вдвое больше, чем восемь в оригинальном Brainfuck.
//
// Первая восьмёрка (как в Brainfuck):
//     ♠  Десница: указатель вправо            (Brainfuck: >)
//     ♣  Шуйца:  указатель влево              (Brainfuck: <)
//     ♥  Благодать: ячейка +1                 (Brainfuck: +)
//     ♦  Смирение: ячейка −1                  (Brainfuck: -)
//     ☦  Возвестие: вывести ячейку            (Brainfuck: .)
//     ✞  Откровение: считать символ с ввода   (Brainfuck: ,)
//     ✟  Молитва: начало цикла                (Brainfuck: [)
//     ✠  Аминь: конец цикла                   (Brainfuck: ])
//
// Вторая восьмёрка (сверх Brainfuck):
//     ✝  Крест: очистить ячейку (c = 0)
//     ☚  Шуйца-указ: tape[ptr−1] += c
//     ☛  Десница-указ: tape[ptr+1] += c
//     ✖  Андреевский крест: c = c × tape[ptr+1] (mod 256)
//     ☨  Крест Лотарингии: обменять c с правым соседом
//     ☧  Хриограмма: c = 2c (mod 256)
//     ☥  Крест с рукоятью: вывести c как десятичное число
//     Ω  Омега: немедленно остановить программу
//
// Всё прочее — мирская суета: не выполняется.
//
// Сборка:  g++ -std=c++17 -O2 -o hbf hbf.cpp
// Запуск:  ./hbf examples/hello.hbf
//          echo -n A | ./hbf examples/next_char.hbf
//          ./hbf -e '♥♥♥♠♥♥♥♥♥♥♥♣✖☥'   # 3 × 7 = 21

#include <cstdint>
#include <cstdio>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

#include <unistd.h>

namespace {

constexpr std::size_t kTapeSize = 30000;
constexpr std::uint8_t kEofValue = 0;

enum class Op : std::uint8_t {
    Right,
    Left,
    Inc,
    Dec,
    Out,
    In,
    LoopStart,
    LoopEnd,
    Clear,
    AddLeft,
    AddRight,
    Mul,
    Swap,
    Double,
    NumOut,
    Halt,
};

struct Program {
    std::vector<Op> code;
    std::vector<std::size_t> jump;  // для циклов: jump[i] — парная позиция
};

// Разбор UTF-8 в последовательность кодовых точек.
bool utf8Decode(const std::string& s, std::vector<std::uint32_t>& out) {
    std::size_t i = 0;
    while (i < s.size()) {
        const auto c = static_cast<unsigned char>(s[i]);
        std::uint32_t cp = 0;
        std::size_t len = 0;
        if (c < 0x80) {
            cp = c;
            len = 1;
        } else if ((c & 0xE0) == 0xC0) {
            cp = c & 0x1Fu;
            len = 2;
        } else if ((c & 0xF0) == 0xE0) {
            cp = c & 0x0Fu;
            len = 3;
        } else if ((c & 0xF8) == 0xF0) {
            cp = c & 0x07u;
            len = 4;
        } else {
            return false;
        }
        if (i + len > s.size()) {
            return false;
        }
        for (std::size_t j = 1; j < len; ++j) {
            const auto cc = static_cast<unsigned char>(s[i + j]);
            if ((cc & 0xC0) != 0x80) {
                return false;
            }
            cp = (cp << 6) | (cc & 0x3Fu);
        }
        out.push_back(cp);
        i += len;
    }
    return true;
}

// Священный знак → операция. false для мирской суеты.
bool sacredOp(std::uint32_t cp, Op& op) {
    switch (cp) {
        // Первая восьмёрка
        case 0x2660: op = Op::Right;     break;  // ♠
        case 0x2663: op = Op::Left;      break;  // ♣
        case 0x2665: op = Op::Inc;       break;  // ♥
        case 0x2666: op = Op::Dec;       break;  // ♦
        case 0x2626: op = Op::Out;       break;  // ☦
        case 0x271E: op = Op::In;        break;  // ✞
        case 0x271F: op = Op::LoopStart; break;  // ✟
        case 0x2720: op = Op::LoopEnd;   break;  // ✠
        // Вторая восьмёрка
        case 0x271D: op = Op::Clear;     break;  // ✝
        case 0x261A: op = Op::AddLeft;   break;  // ☚
        case 0x261B: op = Op::AddRight;  break;  // ☛
        case 0x2716: op = Op::Mul;       break;  // ✖
        case 0x2628: op = Op::Swap;      break;  // ☨
        case 0x2627: op = Op::Double;    break;  // ☧
        case 0x2625: op = Op::NumOut;    break;  // ☥
        case 0x03A9: op = Op::Halt;      break;  // Ω
        default: return false;
    }
    return true;
}

// Очистить источник от мирской суеты, проверить пары «молитв» и «аминь».
bool compile(const std::string& source, Program& prog, std::string& err) {
    std::vector<std::uint32_t> cps;
    if (!utf8Decode(source, cps)) {
        err = "некорректная кодировка UTF-8";
        return false;
    }
    for (const auto cp : cps) {
        Op op;
        if (sacredOp(cp, op)) {
            prog.code.push_back(op);
        }
    }

    prog.jump.assign(prog.code.size(), 0);
    std::vector<std::size_t> stack;
    for (std::size_t i = 0; i < prog.code.size(); ++i) {
        if (prog.code[i] == Op::LoopStart) {
            stack.push_back(i);
        } else if (prog.code[i] == Op::LoopEnd) {
            if (stack.empty()) {
                err = "лишний «аминь» (✠) — позиция " + std::to_string(i) +
                      " в священном коде";
                return false;
            }
            const auto j = stack.back();
            stack.pop_back();
            prog.jump[i] = j;
            prog.jump[j] = i;
        }
    }
    if (!stack.empty()) {
        err = "незакрытая «молитва» (✟) — позиция " +
              std::to_string(stack.back()) + " в священном коде";
        return false;
    }
    return true;
}

// Выполнить программу, вернуть байты вывода.
std::string run(const Program& prog, const std::string& input) {
    std::vector<std::uint8_t> tape(kTapeSize, 0);
    std::size_t ptr = 0;
    std::size_t ip = 0;
    std::size_t inPos = 0;
    std::string out;

    while (ip < prog.code.size()) {
        const std::size_t right = (ptr + 1) % kTapeSize;
        const std::size_t left = (ptr + kTapeSize - 1) % kTapeSize;
        switch (prog.code[ip]) {
            case Op::Right:
                ptr = right;
                break;
            case Op::Left:
                ptr = left;
                break;
            case Op::Inc:
                tape[ptr] = static_cast<std::uint8_t>(tape[ptr] + 1);
                break;
            case Op::Dec:
                tape[ptr] = static_cast<std::uint8_t>(tape[ptr] - 1);
                break;
            case Op::Out:
                out.push_back(static_cast<char>(tape[ptr]));
                break;
            case Op::In:
                tape[ptr] = (inPos < input.size())
                                ? static_cast<std::uint8_t>(input[inPos++])
                                : kEofValue;
                break;
            case Op::LoopStart:
                if (tape[ptr] == 0) {
                    ip = prog.jump[ip];
                }
                break;
            case Op::LoopEnd:
                if (tape[ptr] != 0) {
                    ip = prog.jump[ip];
                }
                break;
            case Op::Clear:
                tape[ptr] = 0;
                break;
            case Op::AddLeft:
                tape[left] = static_cast<std::uint8_t>(tape[left] + tape[ptr]);
                break;
            case Op::AddRight:
                tape[right] = static_cast<std::uint8_t>(tape[right] + tape[ptr]);
                break;
            case Op::Mul:
                tape[ptr] = static_cast<std::uint8_t>(tape[ptr] * tape[right]);
                break;
            case Op::Swap:
                std::swap(tape[ptr], tape[right]);
                break;
            case Op::Double:
                tape[ptr] = static_cast<std::uint8_t>(tape[ptr] * 2);
                break;
            case Op::NumOut:
                out += std::to_string(tape[ptr]);
                break;
            case Op::Halt:
                return out;
        }
        ++ip;
    }
    return out;
}

std::string readAll(std::istream& in) {
    std::string data;
    char buf[4096];
    while (in) {
        in.read(buf, sizeof(buf));
        data.append(buf, static_cast<std::size_t>(in.gcount()));
    }
    return data;
}

bool readFile(const std::string& path, std::string& out, std::string& err) {
    std::ifstream f(path, std::ios::binary);
    if (!f) {
        err = "не удалось открыть священный текст: " + path;
        return false;
    }
    out = readAll(f);
    return true;
}

void usage(std::FILE* stream) {
    std::fputs(
        "Святой Брейнфак (Holy Brainfuck) — интерпретатор, 16 команд.\n"
        "Использование:\n"
        "  hbf <файл>            выполнить программу из файла\n"
        "  hbf -e 'программа'    выполнить программу из строки\n"
        "  --stdin <файл>        данные для команды ✞ (иначе — стандартный ввод)\n",
        stream);
}

}  // namespace

int main(int argc, char* argv[]) {
    std::string file;
    std::string evalCode;
    bool hasEval = false;
    std::string stdinFile;

    for (int i = 1; i < argc; ++i) {
        const std::string arg = argv[i];
        if (arg == "-e" || arg == "--eval") {
            if (i + 1 >= argc) {
                std::fputs("после -e нужна строка с программой\n", stderr);
                return 2;
            }
            evalCode = argv[++i];
            hasEval = true;
        } else if (arg == "--stdin") {
            if (i + 1 >= argc) {
                std::fputs("после --stdin нужен путь к файлу\n", stderr);
                return 2;
            }
            stdinFile = argv[++i];
        } else if (arg == "-h" || arg == "--help") {
            usage(stdout);
            return 0;
        } else if (!arg.empty() && arg[0] == '-') {
            std::fprintf(stderr, "неизвестная опция: %s\n", arg.c_str());
            usage(stderr);
            return 2;
        } else if (!file.empty()) {
            std::fputs("укажите лишь один файл с программой\n", stderr);
            return 2;
        } else {
            file = arg;
        }
    }

    if (hasEval && !file.empty()) {
        std::fputs("укажите либо файл, либо -e, но не оба сразу\n", stderr);
        return 2;
    }
    if (!hasEval && file.empty()) {
        usage(stderr);
        return 2;
    }

    std::string source;
    if (hasEval) {
        source = evalCode;
    } else {
        std::string err;
        if (!readFile(file, source, err)) {
            std::fprintf(stderr, "%s\n", err.c_str());
            return 1;
        }
    }

    std::string input;
    if (!stdinFile.empty()) {
        std::string err;
        if (!readFile(stdinFile, input, err)) {
            std::fprintf(stderr, "%s\n", err.c_str());
            return 1;
        }
    } else if (!isatty(STDIN_FILENO)) {
        input = readAll(std::cin);
    }

    Program prog;
    std::string err;
    if (!compile(source, prog, err)) {
        std::fprintf(stderr, "Ошибка освящения: %s\n", err.c_str());
        return 1;
    }

    const std::string out = run(prog, input);
    if (!out.empty()) {
        std::fwrite(out.data(), 1, out.size(), stdout);
    }
    return 0;
}
