#!/bin/bash


# Укажите желаемый логин
username="test"

# Генерируем случайный пароль
password=$(head /dev/urandom | tr -dc A-Za-z0-9 | head -c 12)

# Создаем пользователя с указанным логином
useradd -m "$username"

# Устанавливаем сгенерированный пароль для нового пользователя
echo "$username:$password" | sudo chpasswd

# Создаем директорию для хранения информации
info_dir="/home/poison/info"
mkdir -p "$info_dir"

# Записываем логин и пароль в файл
echo "Логин: $username" > "$info_dir/login_pas.txt"
echo "Пароль: $password" >> "$info_dir/login_pas.txt"

echo "Пользователь успешно создан. Логин и пароль сохранены в файле: $info_dir/login_pas.txt"
echo ""

test_dir="/home/test"
user_dir="/home/poison"

groups=("group1" "group2" "group3" "group4" "group5" "group6" "group7" "group8")
password_file="$info_dir/passwords.txt"

# Путь к файлу /etc/gshadow
gshadow_file="/etc/gshadow"

# Генерация дерева директорий
derevo_dir="$test_dir/derevo"

root_file="$info_dir/generated_phrase.txt"

groups_dir="$test_dir/groups"

#Файл с номером группы и файлом, куда был помещен пароль
group_info="$info_dir/groups.txt"

temp_dir="$user_dir/temp"

archive="/mnt/host_archive/RFC-all.tar.gz"



#!СОЗДАНИЕ ГРУПП, ЗАДАНИЕ ПАРОЛЕЙ, ЗАПИСЬ В ФАЙЛ


# Создание групп и задание паролей


echo "Генерация паролей и создание групп..."
echo ""

generated_passwords=()

for group in "${groups[@]}"; do

    #Создание групп
    groupadd "$group"

    # Генерация случайной соли
    salt=$(openssl rand -base64 8)

    # Генерация случайного пароля
    generated_password=$(openssl rand -base64 12)

    generated_passwords+=("$generated_password")

    # Генерация зашифрованного пароля с openssl passwd
    encrypted_password=$(openssl passwd -1 -salt $salt $generated_password)

    # Замена пароля в файле /etc/gshadow для указанной группы
    sed -i "s|^$group:!::|$group:$encrypted_password::|g" $gshadow_file

    # Вывод сообщения об успешном изменении пароля
    echo "Пароль для группы $group изменен на: $generated_password"
    echo ""

    echo "$group:$generated_password" >> "$password_file"

done



#!ГЕНЕРАЦИЯ ДЕРЕВА ДИРЕКТОРИЙ



mkdir -p "$derevo_dir"

echo "Генерация дерева директорий..."
echo ""

generate_random_name() {
    echo "$(head /dev/urandom | tr -dc 'a-zA-Z' | fold -w 7 | head -n 1)"
}

generate_directories() {
    local num_levels=$1
    local current_level=$2
    local parent_dir=$3

    if [ $current_level -gt $num_levels ]; then
        return
    fi

    for ((i=1; i<=5; i++)); do
        random_name=$(generate_random_name)
        current_dir="$parent_dir/$random_name"
        mkdir -p "$current_dir"
        #echo "Created directory: $current_dir"

        # Присвоение случайной группы, если массив не пуст
        if [ "${#groups[@]}" -gt 0 ]; then
            random_group=${groups[$((RANDOM % ${#groups[@]}))]}
            chown :"$random_group" "$current_dir"
            chmod 750 "$current_dir"
        fi

        # Рекурсивный вызов для следующего уровня
        (cd "$current_dir" && generate_directories $num_levels $((current_level+1)) "$current_dir")
    done
}

# Генерация дерева директорий с 5 уровнями
generate_directories 5 1 "$derevo_dir"



#!ЗАПИСЬ ПАРОЛЕЙ ОТ ГРУПП В ФАЙЛЫ


# Создание директории для групп

mkdir -p "$groups_dir"

# Выбор случайного файла RFC для каждой группы
group_files=()

# Создание файла для каждой группы
for ((i=0; i<${#groups[@]}; i++)); do
    group="${groups[$i]}"

	# Выбор случайного файла RFC
	random_rfc_file=$(tar -tf "$archive" | grep 'RFC*' | shuf -n 1)

    group_file="$groups_dir/$(basename $random_rfc_file)"
    group_files+=("$group_file")

    tar -C "$groups_dir" -xzf "$archive" "$random_rfc_file"

	# Проверка наличия пароля для группы
    if [ -n "${generated_passwords[$i]}" ]; then
        random_position=$(shuf -i 1-$(wc -l < "$group_file") -n 1)

        # Вывод информации о месте вставки пароля
        echo "Добавляем пароль в файл для группы $group: $group_file"
        echo ""
        echo "Место вставки (строка): $random_position"
        echo ""
        echo "$group: $group_file" >> "$group_info"

        new_phrase="   $group – ${generated_passwords[$i]}"
        awk -v pos="$random_position" -v phrase="$new_phrase" 'NR==pos {$0=phrase "\n" $0} {print}' "$group_file" > temp && mv temp "$group_file"

        if [ $i -eq 0 ]; then
            chgrp "$username" "$group_file"
            chmod 750 "$group_file"
        else
            prev_group="${groups[$((i-1))]}"
            chgrp "$prev_group" "$group_file"
            chmod 750 "$group_file"
        fi

    fi

done


#!ГЕНЕРАЦИЯ ФРАЗЫ И ЗАПИСЬ ЕЕ В ФАЙЛ


# Создание временной директории

mkdir -p "$temp_dir"

# Выбор случайного файла RFC
for i in {1..7}; do
    random_rfc_file=$(tar -tf "$archive" | grep 'RFC*' | shuf -n 1)

    # Получение оригинального названия файла
    original_filename=$(basename "$random_rfc_file")

    # Копирование файла RFC во временную директорию с новым именем
    copied_rfc_file="$temp_dir/$original_filename"
    # cp "$random_rfc_file" "$copied_rfc_file"

    tar -C "$temp_dir" -xzf "$archive" "$random_rfc_file"

    # Генерация случайного пароля для шифрования
    encryption_password=$(openssl rand -base64 16)

    # Если это первый файл, генерируем и вставляем фразу
    if [ $i -eq 1 ]; then
        # Генерация случайной фразы на английском языке
        random_phrase="   (\\\\$(shuf -n 6 /usr/share/dict/words | tr '\n' ' ' | sed 's/ $/\\\\./')"

        # Получение случайной позиции в файле
        random_position=$(shuf -i 1-$(wc -l < "$copied_rfc_file") -n 1)

        # Вставка фразы в случайное место в файле
        awk -v pos="$random_position" -v phrase="$random_phrase" '{if (NR==pos) print phrase}1' "$copied_rfc_file" > temp && mv temp "$copied_rfc_file"

        new_phrase=$(echo "$random_phrase" | sed 's/\\\\/\\/g')

        # Вывод информации о созданном файле во временной директории
        echo "Создан файл с вставленной фразой: $copied_rfc_file"
        echo ""
        echo "Фраза: $new_phrase"
        echo ""
		echo "Место вставки (строка) фразы: $random_position"
		echo ""
        # Вывод сгенерированной фразы в отдельный файл для проверки
        echo "$new_phrase" > "$root_file"

    fi

    # Присвоение случайной группы исходному файлу
    file_group=${groups[$((RANDOM % ${#groups[@]}))]}
    chown :"$file_group" "$temp_dir/$original_filename"
    chmod 750 "$temp_dir/$original_filename"

    # Шифрование файла без интерактивного режима
    gpg --batch --yes --passphrase "$encryption_password" --output "$temp_dir/$original_filename.gpg" --symmetric "$copied_rfc_file"

	# Запись пароля в файл
    echo "$original_filename.gpg : $encryption_password" >> "$info_dir/pass_shifr.txt"

    # Присвоение случайной группы зашифрованному файлу
    file_group=${groups[$((RANDOM % ${#groups[@]}))]}
    chown :"$file_group" "$temp_dir/$original_filename.gpg"
    chmod 750 "$temp_dir/$original_filename.gpg"

    # Создание фразы с указанием зашифрованного файла и пароля к нему
    pass_shifr_phrase="   $original_filename.gpg – $encryption_password"

    echo "Shifr fraza: $pass_shifr_phrase"
    echo ""

    # Выбор RFC файла для записи пароля от зашифрованного файла
    random_rfc_file_for_pass_shifr=$(tar -tf "$archive" | grep 'RFC*' | shuf -n 1)

    # Выбор директории для размещения файла с паролем
    random_subdir_for_file_shifr_pass=$(find "$derevo_dir" -type d | shuf -n 1)

    # Определение случайного пути
    shifr_pass_path="$random_subdir_for_file_shifr_pass/$(basename $random_rfc_file_for_pass_shifr)"

    # Копирование RFC файла по случайному пути
    # cp "$random_rfc_file_for_pass_shifr" "$shifr_pass_path"

    tar -C "$random_subdir_for_file_shifr_pass" -xzf "$archive" "$random_rfc_file_for_pass_shifr"

    # Получение случайной позиции в файле
    random_position=$(shuf -i 1-$(wc -l < "$shifr_pass_path") -n 1)

    # Вставка фразы в случайное место в файле
    awk -v pos="$random_position" -v phrase="$pass_shifr_phrase" '{if (NR==pos) print phrase; else print $0}' "$shifr_pass_path" > temp && mv temp "$shifr_pass_path"

    # Присвоение случайной группы файлу с паролем от зашифрованного файла
    file_group=${groups[$((RANDOM % ${#groups[@]}))]}
    chown :"$file_group" "$shifr_pass_path"
    chmod 750 "$shifr_pass_path"

	# Запись информации о местоположении файла с паролем от зашифрованного файла
    echo "$shifr_pass_path" : "$encryption_password" : $random_position >> "$info_dir/rfc_with_shifr_pass.txt"

    echo "Путь файла с паролем от зашифрованного файла: $shifr_pass_path"
    echo ""

    echo "Место вставки (строка) пароля: $random_position"
    echo ""

    tar -czf "$temp_dir/$original_filename.tar.gz" -C "$temp_dir" "$original_filename.gpg"

    # Выбор случайной директории
    random_subdir=$(find "$derevo_dir" -type d | shuf -n 1)

    random_name=$(generate_random_name)

    # Перемещение зашифрованного файла в случайную директорию с оригинальным названием
    mv "$temp_dir/$original_filename.tar.gz" "$random_subdir/$random_name.tar.gz"

    # Присвоение случайной группы архиву
    file_group=${groups[$((RANDOM % ${#groups[@]}))]}
    chown :"$file_group" "$random_subdir/$random_name.tar.gz"
    chmod 750 "$random_subdir/$random_name.tar.gz"


    # Вывод информации о перемещенном файле
    echo "Архив перемещен в директорию: $random_subdir"
    echo ""
    echo "Архиву присвоена группа: $file_group"
    echo ""
    echo "Оригинальное название файла: $original_filename"
    echo ""
    echo "Случайное название файла: $random_name.tar.gz"
    echo ""


done

# Удаление временной директории
rm -r $temp_dir

sync; sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches' && sudo swapoff -a && sudo swapon -a
history -r
history -cw
echo > "/root/.bash_history"
echo > "/poison/.bash_history"
echo > "/var/log/wtmp"
echo > "/var/log/btmp"
echo > "/var/log/error"
echo > "/var/log/debug"
echo > "/var/log/lastlog"
echo > "/var/log/syslog"
echo > "/var/log/auth.log"
echo > "/var/log/cron.log"
echo > "/var/log/kern.log"
echo > "/var/log/user.log"
echo > "/var/log/daemon.log"
echo > "/var/log/audit/audit.log"
echo > "/var/log/messages"
echo > "/parsec/log/astra/events"
sudo journalctl --rotate
sudo journalctl --vacuum-time=1s

rm -r "/root/.gnupg"
rm -r "/home/poison/.gnupg"

echo "Готово!"

rm -- "$0"
