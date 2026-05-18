import csv

with open('data/processed/cache/existing/existingArticlesPROD.csv', 'r', encoding='utf-8-sig') as f:
    # Read first 3 lines as raw text
    for i in range(3):
        line = f.readline()
        print(f'Line {i}: {repr(line)}')
    f.seek(0)
    # Try reading with DictReader
    reader = csv.DictReader(f, delimiter=',')
    print(f'Fieldnames: {reader.fieldnames}')
    for i, row in enumerate(reader):
        if i < 3:
            print(f'Row {i}: {row}')
        if i > 5:
            break
