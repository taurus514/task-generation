#!/bin/bash

# Укажите путь к архиву
archive_path="/home/user/RFC-all.tar.gz"

# Укажите путь к целевой директории
target_dir="/root/archive/RFC-all"

mkdir -p "$target_dir"

# Распаковываем архив в целевую директорию
tar -xzf "$archive_path" -C "$target_dir" --wildcards '*.txt'

# Переходим в целевую директорию
cd "$target_dir" || exit

rm -r "$target_dir/a"

# Переименовываем файлы rfc[:alpha:].txt в RFC[:alpha:]
for file in rfc*.txt; do
    new_name=$(echo "$file" | sed 's/rfc/RFC/' | sed 's/\.txt//')
    mv "$file" "$new_name"
done

rm "$target_dir/RFC-index"

echo "Архив успешно распакован и обработан в директории: $target_dir"
