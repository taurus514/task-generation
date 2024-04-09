qt.py - программное средство генерации заданий
gg.sh - скрипт для создания заданий
RFC.sh - скрипт для извлечения из архива, который содержит файлы RFC, файлов формата *.txt

Для подготовки к функционированию средства генерации практических заданий необходимо выполнить следующие шаги:

1. Сперва необходимо скачать архив с сайта https://www.rfc-editor.org/in-notes/tar/RFC-all.tar.gz

2. Затем следует извлечь файлы с помощью скрипта RFC.sh в директорию /root/space/archive

3. Далее необходимо разместить файл gg.sh в директорию /root/scripts

Если размещение осуществляется в других директориях, необходимо указать пути в файле qt.py в строках 53 для размещения архива с файлами RFC и 440 для размещения скриптов создания заданий.

4. Далее необходимо установить средство контейнеризации Docker и дополнительные библиотеки Python командой:

sudo apt install docker.io python3-docker python3-pyqt5

5. Следующим шагом является подготовка архива, которя осуществляется определенной последовательностью действий.
  
  1)	Необходимо установить утилиту qemu-utils командой:

  apt-get install qemu-utils

  2)	Загрузить файл диска, имеющего формат vmdk, подготовленной в минимальной конфигурации виртуальной машины в ОССН Astra Linux SE, в которой развернуто средство контейнеризации Docker.
  
  3)	Конвертировать vmdk в raw, с использованием утилиты qemu-img. Это преобразует образ диска в формат, аналогичный прямому дампу с /dev/sda. Команда для этого: 

  qemu-img convert -f vmdk MyDisk.vmdk -O raw MyDisk.raw

  где MyDisk.vmdk – файл диска заранее подготовленной виртуальной машины; 
  MyDisk.raw – название создаваемого при конвертировании файла.

  4)	После завершения процесса преобразования необходимо посмотреть таблицу разделов нового raw-файла, чтобы получить данные, необходимые для монтирования файла для дальнейшего использования, следующей командой:

  parted -s MyDisk.raw unit b print

  В результате выполнения данной команды в командной строке выводится информация о смещениях разделов, размерах и типах. Важно обратить внимание на значение в столбце Start для загрузочного сектора. В рассматриваемом случае размер составляет 1045876 байт.

  5)	Если раздел простой (например, ext или fat), его можно смонтировать в созданную директорию с помощью команды: 

  sudo mount -o loop,norecovery,ro,offset=1045876 MyDisk.raw ./mnt

  где offset=1045876 – размер, указанный в столбце Start;
  mnt – директория, созданная для монтирования.

  Если раздел управляется Logical Volume Management (далее – LVM), требуется несколько дополнительных шагов, включая настройку устройства loop и сканирование содержимого для генерации устройств разделов.
  
  6)	После монтирования раздела необходимо создать tar-архив с содержимым, который затем импортируется в Docker. Команда для создания tar-архива: 

  sudo tar -C mnt -czf MyDisk.tar.gz .

  где mnt – созданная для монтирования директория;
  MyDisk.tar.gz – название создаваемого tar-архива, который необходимо выгрузить в Docker;
  . – указание места, где будет создан tar-архив.

  7)	Для отмонтирования диска необходимо использовать команду: 

  sudo umount ./mnt 

  8)	Команда для импорта архива в Docker: 

  docker import MyDisk.tar.gz myimage:1.0

  где myimage – название образа в средстве контейнеризации Docker;
  : – разделитель;
  1.0	– версия образа.
  
  Название образа необходимо указать в файле qt.py в строке 439.
