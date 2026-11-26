#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Святой Брейнфак (Holy Brainfuck, HBF) — интерпретатор языка.

16 команд — вдвое больше, чем восемь в оригинальном Brainfuck.

Первая восьмёрка (как в Brainfuck):
    ♠  Десница: указатель вправо
    ♣  Шуйца:  указатель влево
    ♥  Благодать: ячейка +1
    ♦  Смирение: ячейка −1
    ☦  Возвестие: вывести ячейку как символ
    ✞  Откровение: считать символ с ввода
    ✟  Молитва: начало цикла
    ✠  Аминь: конец цикла

Вторая восьмёрка (сверх Brainfuck):
    ✝  Крест: очистить ячейку (c = 0)
    ☚  Шуйца-указ: tape[ptr−1] += c
    ☛  Десница-указ: tape[ptr+1] += c
    ✖  Андреевский крест: c = c × tape[ptr+1] (mod 256)
    ☨  Крест Лотарингии: обменять c с правым соседом
    ☧  Хриограмма: c = 2c (mod 256)
    ☥  Крест с рукоятью: вывести c как десятичное число
    Ω  Омега: немедленно остановить программу

Всё прочее — мирская суета: не выполняется.

Примеры:
    python3 hbf.py examples/hello.hbf
    echo -n A | python3 hbf.py examples/next_char.hbf
    python3 hbf.py -e '♥♥♥♠♥♥♥♥♥♥♥♣✖☥'   # 3 × 7 = 21
"""
from __future__ import annotations

import argparse
import sys

TAPE_SIZE = 30_000
EOF_VALUE = 0

# Кодовая точка священного знака → операция
TRANSLATION = {
    # Первая восьмёрка
    0x2660: "right",    # ♠
    0x2663: "left",     # ♣
    0x2665: "inc",      # ♥
    0x2666: "dec",      # ♦
    0x2626: "out",      # ☦
    0x271E: "in",       # ✞
    0x271F: "[",        # ✟
    0x2720: "]",        # ✠
    # Вторая восьмёрка
    0x271D: "clear",    # ✝
    0x261A: "addle",    # ☚
    0x261B: "addr",     # ☛
    0x2716: "mul",      # ✖
    0x2628: "swap",     # ☨
    0x2627: "double",   # ☧
    0x2625: "num",      # ☥
    0x03A9: "halt",     # Ω
}


def compile_source(source: str) -> list[str]:
    """Очистить источник от мирской суеты, оставив только священные знаки."""
    return [TRANSLATION[ord(ch)] for ch in source if ord(ch) in TRANSLATION]


def match_brackets(code: list[str]) -> dict[int, int]:
    """Сопоставить позиции «молитв» (✟) и «аминь» (✠)."""
    pairs: dict[int, int] = {}
    stack: list[int] = []
    for i, op in enumerate(code):
        if op == "[":
            stack.append(i)
        elif op == "]":
            if not stack:
                raise SyntaxError(f"лишний «аминь» (✠) — позиция {i} в священном коде")
            j = stack.pop()
            pairs[i] = j
            pairs[j] = i
    if stack:
        raise SyntaxError(
            f"незакрытая «молитва» (✟) — позиция {stack[-1]} в священном коде"
        )
    return pairs


def run(source: str, stdin: bytes = b"", *, echo: bool = False) -> bytes:
    """Выполнить программу на Святом Брейнфаке, вернуть байты вывода.

    echo=True — дополнительно писать вывод в sys.stdout по мере исполнения.
    """
    code = compile_source(source)
    pairs = match_brackets(code)

    tape = bytearray(TAPE_SIZE)
    ptr = 0
    out = bytearray()
    ip = 0
    in_pos = 0

    while ip < len(code):
        op = code[ip]
        if op == "right":
            ptr = (ptr + 1) % TAPE_SIZE
        elif op == "left":
            ptr = (ptr - 1) % TAPE_SIZE
        elif op == "inc":
            tape[ptr] = (tape[ptr] + 1) % 256
        elif op == "dec":
            tape[ptr] = (tape[ptr] - 1) % 256
        elif op == "out":
            out.append(tape[ptr])
            if echo:
                sys.stdout.buffer.write(bytes([tape[ptr]]))
                sys.stdout.buffer.flush()
        elif op == "in":
            if in_pos < len(stdin):
                tape[ptr] = stdin[in_pos]
                in_pos += 1
            else:
                tape[ptr] = EOF_VALUE
        elif op == "[":
            if tape[ptr] == 0:
                ip = pairs[ip]
        elif op == "]":
            if tape[ptr] != 0:
                ip = pairs[ip]
        elif op == "clear":
            tape[ptr] = 0
        elif op == "addle":
            left = (ptr - 1) % TAPE_SIZE
            tape[left] = (tape[left] + tape[ptr]) % 256
        elif op == "addr":
            right = (ptr + 1) % TAPE_SIZE
            tape[right] = (tape[right] + tape[ptr]) % 256
        elif op == "mul":
            right = (ptr + 1) % TAPE_SIZE
            tape[ptr] = (tape[ptr] * tape[right]) % 256
        elif op == "swap":
            right = (ptr + 1) % TAPE_SIZE
            tape[ptr], tape[right] = tape[right], tape[ptr]
        elif op == "double":
            tape[ptr] = (tape[ptr] * 2) % 256
        elif op == "num":
            text = str(tape[ptr]).encode("ascii")
            out.extend(text)
            if echo:
                sys.stdout.buffer.write(text)
                sys.stdout.buffer.flush()
        elif op == "halt":
            break
        ip += 1

    return bytes(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="hbf",
        description="Святой Брейнфак (Holy Brainfuck) — интерпретатор, 16 команд.",
    )
    parser.add_argument("file", nargs="?", help="файл программы (.hbf)")
    parser.add_argument("-e", "--eval", dest="code", help="программа в виде строки")
    parser.add_argument(
        "--stdin",
        dest="stdin_file",
        help="файл с данными для команды ✞ "
        "(иначе читается стандартный ввод, если он не терминал)",
    )
    args = parser.parse_args(argv)

    if args.code is not None and args.file:
        parser.error("укажите либо файл, либо -e, но не оба сразу")

    if args.code is not None:
        source = args.code
    elif args.file:
        try:
            with open(args.file, encoding="utf-8") as f:
                source = f.read()
        except OSError as exc:
            print(f"Не удалось открыть священный текст: {exc}", file=sys.stderr)
            return 1
    else:
        parser.error("укажите файл с программой или -e 'программа'")

    data = b""
    if args.stdin_file:
        try:
            with open(args.stdin_file, "rb") as f:
                data = f.read()
        except OSError as exc:
            print(f"Не удалось прочитать ввод: {exc}", file=sys.stderr)
            return 1
    elif not sys.stdin.isatty():
        data = sys.stdin.buffer.read()

    try:
        run(source, data, echo=True)
    except SyntaxError as exc:
        print(f"Ошибка освящения: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
