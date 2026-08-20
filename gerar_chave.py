"""Painel gerador de chaves de licença (uso exclusivo do administrador).

Uso:
    python gerar_chave.py
    python gerar_chave.py --dias 7
    python gerar_chave.py --dias 30 --qtd 5
"""
import argparse
import sys

from src.license_manager import generate_key


PRESETS = {
    "1": 1,
    "2": 7,
    "3": 30,
    "4": 90,
    "5": 365,
}


def _interactive() -> tuple[int, int]:
    print("=" * 50)
    print("  Gerador de Chaves - Analisador Viral")
    print("=" * 50)
    print()
    print("Escolha a duração da chave:")
    print("  1)  1 dia")
    print("  2)  7 dias")
    print("  3)  30 dias")
    print("  4)  90 dias")
    print("  5)  365 dias")
    print("  6)  Personalizado (digitar N dias)")
    print()

    while True:
        choice = input("Opção: ").strip()
        if choice in PRESETS:
            days = PRESETS[choice]
            break
        if choice == "6":
            try:
                days = int(input("Quantos dias? "))
                if days < 1:
                    print("Deve ser pelo menos 1 dia. Tente novamente.")
                    continue
                break
            except ValueError:
                print("Digite um número válido.")
                continue
        print("Opção inválida.")

    while True:
        qtd_raw = input("Quantas chaves gerar? [1]: ").strip() or "1"
        try:
            qtd = int(qtd_raw)
            if qtd < 1:
                print("Deve ser pelo menos 1.")
                continue
            break
        except ValueError:
            print("Digite um número válido.")

    return days, qtd


def main():
    parser = argparse.ArgumentParser(description="Gera chaves de licença do Analisador Viral.")
    parser.add_argument("--dias", type=int, help="Duração da chave em dias.")
    parser.add_argument("--qtd", type=int, default=1, help="Quantidade de chaves a gerar.")
    args = parser.parse_args()

    if args.dias is None:
        days, qtd = _interactive()
    else:
        if args.dias < 1:
            print("Erro: --dias deve ser >= 1", file=sys.stderr)
            sys.exit(1)
        days, qtd = args.dias, args.qtd

    print()
    print(f"Gerando {qtd} chave(s) de {days} dia(s):")
    print("-" * 50)
    for i in range(qtd):
        key = generate_key(days)
        print(f"  {i + 1}. {key}")
    print("-" * 50)
    print()
    print("Anote a que enviar para cada cliente. A validade começa a contar")
    print("no momento em que o cliente ativar a chave dentro do app.")


if __name__ == "__main__":
    main()
