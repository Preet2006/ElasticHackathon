with open('app/agents/red_team.py', encoding='utf-8') as f:
    lines = f.readlines()

triple_quote_count = 0
for i, line in enumerate(lines, 1):
    count = line.count('"""')
    if count > 0:
        triple_quote_count += count
        state = "OPEN" if triple_quote_count % 2 == 1 else "CLOSED"
        print(f"Line {i:4d}: {count} x \"\"\" -> Total: {triple_quote_count} ({state}) | {line[:70].rstrip()}")

print(f"\nFinal: {triple_quote_count} triple quotes ({'ODD - UNCLOSED!' if triple_quote_count % 2 == 1 else 'EVEN - OK'})")
