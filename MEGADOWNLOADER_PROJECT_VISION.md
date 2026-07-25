# MegaDownloader Video & Audio
## Project Vision и полная дорожная карта

**Рабочее название:** MegaDownloader Video & Audio  
**Тип продукта:** Web SaaS + self-hosted open-source media workspace  
**Текущий фундамент:** Python CLI, `yt-dlp`, FFmpeg  
**Основная идея:** единое веб-пространство для скачивания, извлечения, обрезки, конвертации и повторного использования онлайн-медиа.

---

# 1. Краткое описание проекта

MegaDownloader — это веб-приложение, в котором пользователь вставляет ссылку на видео, аудио или плейлист и получает все доступные действия с этим медиа в одном интерфейсе:

- скачать видео;
- скачать только аудио;
- выбрать качество и формат;
- вырезать нужный фрагмент;
- преобразовать фрагмент в GIF, WebP, MP4 loop или WebM loop;
- скачать субтитры;
- получить чистый текст из субтитров;
- обработать плейлист;
- конвертировать локальный файл;
- подготовить медиа под TikTok, Instagram, YouTube Shorts и другие платформы.

Проект не должен восприниматься как очередная кнопка «Download». Его целевая модель — **Media Action Workspace**: пользователь один раз передаёт ссылку или файл, а затем выполняет над ним любое поддерживаемое действие.

---

# 2. Проблема, которую решает проект

Сегодня пользователю часто приходится пользоваться несколькими сервисами:

1. один сайт — чтобы скачать видео;
2. другой — чтобы извлечь MP3;
3. третий — чтобы обрезать фрагмент;
4. четвёртый — чтобы сделать GIF;
5. пятый — чтобы скачать субтитры;
6. отдельный редактор — чтобы подготовить вертикальный ролик.

Такие сервисы часто перегружены рекламой, имеют ложные кнопки загрузки, плохо объясняют форматы, требуют повторной загрузки одного и того же файла и не дают нормального контроля над результатом.

MegaDownloader объединяет эти операции в одну последовательность:

```text
URL или локальный файл
        ↓
Анализ медиа
        ↓
Выбор действия
        ↓
Настройка параметров
        ↓
Фоновая обработка
        ↓
Скачивание результата
```

---

# 3. Продуктовое видение

## 3.1. Основное обещание

> Вставьте одну ссылку и получите все доступные действия с видео или аудио в одном простом рабочем пространстве.

## 3.2. Расширенное позиционирование

> MegaDownloader помогает скачать, извлечь, обрезать, преобразовать и подготовить онлайн-медиа для повторного использования — без сложного монтажа и без перехода между несколькими сервисами.

## 3.3. Ценность продукта

Проект должен давать пользователю четыре вида ценности:

### Простота
Пользователь не обязан понимать кодеки, контейнеры и параметры FFmpeg.

### Универсальность
Один интерфейс для видео, аудио, плейлистов, субтитров, фрагментов и GIF.

### Контроль
Пользователь выбирает качество, формат, интервал времени и результат обработки.

### Доверие
Никаких ложных кнопок, навязчивых редиректов и скрытых загрузок.

---

# 4. Целевая аудитория

## 4.1. Обычные пользователи

Задачи:

- сохранить видео для личного офлайн-просмотра;
- извлечь аудио;
- скачать песню или подкаст;
- получить небольшой фрагмент;
- создать GIF.

## 4.2. Создатели контента

Задачи:

- получить исходный материал;
- вырезать цитату или эпизод;
- подготовить фрагмент для Shorts, Reels или TikTok;
- скачать субтитры;
- преобразовать видео в другой формат.

## 4.3. Преподаватели, студенты и исследователи

Задачи:

- сохранить лекцию;
- скачать плейлист курса;
- получить субтитры;
- преобразовать субтитры в текст;
- извлечь нужный фрагмент.

## 4.4. Технические пользователи

Задачи:

- self-hosted установка;
- локальная обработка больших файлов;
- пакетная загрузка;
- автоматизация через API;
- расширенные параметры кодеков.

---

# 5. Ключевой пользовательский сценарий

## Шаг 1. Ввод источника

Пользователь:

- вставляет URL;
- или перетаскивает локальный файл;
- или выбирает файл через диалог.

## Шаг 2. Анализ

Система определяет:

- источник;
- тип контента;
- название;
- автора;
- длительность;
- превью;
- доступные форматы;
- разрешения;
- наличие аудио;
- наличие субтитров;
- наличие плейлиста;
- приблизительный размер;
- доступные операции.

## Шаг 3. Выбор действия

Пользователь выбирает:

- Download Video;
- Extract Audio;
- Cut Clip;
- Create GIF;
- Download Subtitles;
- Convert;
- Process Playlist.

## Шаг 4. Настройка

Интерфейс показывает только относящиеся к выбранному действию параметры.

## Шаг 5. Обработка

API создаёт задачу, а отдельный worker выполняет скачивание и обработку.

## Шаг 6. Получение результата

Пользователь видит:

- статус;
- прогресс;
- скорость;
- оставшееся время;
- название результата;
- размер;
- срок автоматического удаления;
- кнопку скачивания.

---

# 6. Основные продуктовые модули

## 6.1. Smart URL Analyzer

Центральный модуль продукта.

### Вход

```json
{
  "url": "https://example.com/video"
}
```

### Выход

```json
{
  "source": "youtube",
  "media_type": "video",
  "title": "Example video",
  "duration_seconds": 742,
  "thumbnail_url": "...",
  "author": "...",
  "is_playlist": false,
  "formats": [],
  "subtitles": [],
  "available_actions": [
    "download_video",
    "extract_audio",
    "cut_clip",
    "create_gif",
    "download_subtitles"
  ]
}
```

### Требования

- анализ без полного скачивания;
- нормализованная модель данных;
- понятные пользовательские ошибки;
- таймаут;
- защита от SSRF;
- кеширование результатов;
- проверка перенаправлений;
- отсутствие shell-инъекций.

---

## 6.2. Video Downloader

Функции:

- выбор разрешения;
- выбор контейнера;
- автоматическое объединение видео и аудио;
- оценка размера;
- пресеты качества;
- скачивание оригинала;
- сохранение метаданных;
- опциональное скачивание thumbnail.

Основные пресеты:

- Best Quality;
- Compatible with Any Device;
- Small File;
- Original Quality;
- Video Only;
- Audio + Video.

---

## 6.3. Audio Downloader / Extractor

Функции:

- извлечение аудио из видео;
- загрузка аудиоконтента;
- MP3, M4A, AAC, WAV, FLAC, Opus;
- выбор битрейта;
- сохранение метаданных;
- сохранение обложки;
- нормализация громкости в будущих версиях.

Пользовательские пресеты:

- Best Audio;
- MP3 Compatible;
- Small File;
- Podcast;
- Lossless.

---

## 6.4. Video Cutter

MVP:

- ручной ввод начала;
- ручной ввод конца;
- валидация диапазона;
- предварительный расчёт длительности;
- фоновая обработка;
- экспорт выбранного фрагмента.

Следующая версия:

- визуальная timeline;
- два draggable-маркера;
- preview;
- waveform;
- несколько фрагментов;
- объединение фрагментов.

---

## 6.5. GIF and Loop Maker

Поддерживаемые результаты:

- GIF;
- animated WebP;
- MP4 loop;
- WebM loop.

Настройки:

- начало;
- конец;
- ширина;
- FPS;
- качество;
- скорость;
- loop;
- crop;
- размер результата.

Пресеты:

- Reaction GIF;
- Telegram;
- Discord;
- Website;
- High Quality;
- Small Size.

---

## 6.6. Subtitle Tools

Функции:

- скачать оригинальные субтитры;
- скачать автоматические субтитры;
- выбрать язык;
- экспортировать SRT;
- экспортировать VTT;
- удалить таймкоды и получить TXT;
- встроить субтитры в видео в будущей версии;
- переводить субтитры в будущей версии.

---

## 6.7. Playlist Downloader

Функции:

- получить список элементов;
- выбрать отдельные элементы;
- выбрать диапазон;
- скачать видео;
- скачать только аудио;
- пронумеровать файлы;
- создать ZIP;
- создать M3U;
- пропускать уже загруженные элементы;
- показывать прогресс каждого элемента и всей задачи.

---

## 6.8. Local File Tools

Пользователь может загрузить собственный файл и использовать:

- cutter;
- converter;
- audio extractor;
- GIF maker;
- compressor;
- metadata reader.

Этот модуль снижает зависимость продукта от изменений сторонних платформ.

---

## 6.9. Social Media Presets

Пресеты:

- TikTok — 9:16;
- Instagram Reels — 9:16;
- Instagram Feed — 4:5 или 1:1;
- YouTube — 16:9;
- YouTube Shorts — 9:16;
- X — 16:9 или 1:1;
- Discord — оптимизированный GIF.

Позднее:

- auto crop;
- blurred background;
- subtitles burn-in;
- safe zones;
- fade-in/fade-out;
- loudness normalization.

---

## 6.10. Workspace Queue

Каждая операция является задачей.

Статусы:

```text
pending
analyzing
queued
downloading
processing
completed
failed
cancelled
expired
```

Карточка задачи показывает:

- название;
- тип;
- источник;
- прогресс;
- скорость;
- текущий этап;
- оставшееся время;
- размер;
- кнопку отмены;
- кнопку повторного запуска;
- кнопку скачивания;
- время удаления результата.

---

# 7. Simple Mode и Advanced Mode

## Simple Mode

Для большинства пользователей:

- URL;
- действие;
- пресет;
- качество;
- Download.

## Advanced Mode

Для опытных пользователей:

- container;
- codec;
- audio codec;
- bitrate;
- frame rate;
- resolution;
- subtitles;
- thumbnail;
- metadata;
- filename template;
- playlist range;
- chapters;
- start/end time.

Главный принцип: расширенные параметры не должны мешать простому сценарию.

---

# 8. UX и визуальное направление

## 8.1. Стиль

Рабочее направление:

> Clean SaaS UI + Soft Neumorphism + лёгкие 3D-декоративные элементы.

Рекомендуемое соотношение:

- 70% чистый SaaS-интерфейс;
- 20% neumorphism;
- 10% декоративные элементы.

## 8.2. Neumorphism применяется для

- segmented controls;
- переключателей;
- выбора формата;
- tool cards;
- timeline handles;
- progress indicators;
- небольших интерактивных панелей.

## 8.3. Обычный контрастный UI применяется для

- основного поля URL;
- CTA;
- ошибок;
- таблиц;
- длинного текста;
- навигации;
- критически важных действий.

## 8.4. Визуальные принципы

- тёплый нейтральный фон;
- белые и светло-бежевые карточки;
- персиковый основной акцент;
- мятный дополнительный акцент;
- большие скругления;
- мягкие тени;
- крупная типографика;
- ясная визуальная иерархия;
- минимальная декоративная перегрузка.

## 8.5. Доступность

Обязательно:

- WCAG-контраст;
- клавиатурная навигация;
- видимые focus states;
- aria-label;
- reduced motion;
- крупные touch targets;
- корректная работа screen reader;
- светлая и тёмная темы.

---

# 9. Информационная архитектура

## Основные страницы

```text
/
├── /video-downloader
├── /audio-downloader
├── /playlist-downloader
├── /video-cutter
├── /video-to-gif
├── /media-converter
├── /subtitle-downloader
├── /supported-sites
├── /how-it-works
├── /faq
├── /blog
├── /privacy
├── /terms
└── /copyright
```

## SEO landing pages

```text
/youtube-video-downloader
/youtube-to-mp3
/youtube-playlist-downloader
/youtube-subtitle-downloader
/tiktok-video-downloader
/instagram-video-downloader
/facebook-video-downloader
/twitter-video-downloader
/soundcloud-downloader
/extract-audio-from-video
/cut-video-by-url
/create-gif-from-video
/webm-to-mp4
/mp4-to-mp3
```

Все страницы используют один общий backend и одну систему задач.

---

# 10. Техническая архитектура

## 10.1. Компоненты

```text
Browser
   ↓
Next.js Web Application
   ↓
FastAPI
   ├── PostgreSQL
   ├── Redis
   ├── Object Storage
   └── Task Queue
          ↓
      Media Worker
      ├── yt-dlp
      └── FFmpeg
```

## 10.2. Почему обработка выполняется в worker

Скачивание и FFmpeg:

- работают долго;
- используют CPU;
- используют диск;
- могут завершиться ошибкой;
- требуют повторных попыток;
- не должны блокировать HTTP-запрос.

Поэтому API только создаёт задачу, а worker выполняет её отдельно.

## 10.3. Рекомендуемый стек

### Frontend

- Next.js;
- TypeScript;
- Tailwind CSS;
- React Hook Form;
- Zod;
- TanStack Query;
- Framer Motion;
- Storybook;
- Playwright.

### Backend

- Python;
- FastAPI;
- Pydantic;
- SQLAlchemy;
- Alembic;
- PostgreSQL;
- Redis;
- Dramatiq или Celery;
- yt-dlp;
- FFmpeg;
- pytest.

### Infrastructure

- Docker;
- Docker Compose;
- Nginx или Traefik;
- S3-compatible storage;
- GitHub Actions;
- structured logging;
- error monitoring;
- metrics.

---

# 11. Предлагаемая структура репозитория

```text
mega-downloader/
├── apps/
│   ├── web/
│   │   ├── app/
│   │   ├── components/
│   │   ├── features/
│   │   ├── hooks/
│   │   ├── lib/
│   │   ├── public/
│   │   ├── styles/
│   │   └── tests/
│   │
│   ├── api/
│   │   ├── app/
│   │   │   ├── api/
│   │   │   ├── core/
│   │   │   ├── models/
│   │   │   ├── schemas/
│   │   │   ├── repositories/
│   │   │   ├── services/
│   │   │   └── main.py
│   │   └── tests/
│   │
│   └── worker/
│       ├── tasks/
│       ├── processors/
│       ├── consumers/
│       └── main.py
│
├── packages/
│   ├── downloader-core/
│   │   ├── analyzer/
│   │   ├── downloaders/
│   │   ├── processors/
│   │   ├── converters/
│   │   ├── validators/
│   │   ├── progress/
│   │   ├── models/
│   │   └── exceptions/
│   │
│   └── shared-types/
│
├── storage/
│   ├── temporary/
│   ├── completed/
│   └── thumbnails/
│
├── docs/
│   ├── architecture/
│   ├── api/
│   ├── product/
│   └── adr/
│
├── docker/
├── scripts/
├── .github/
│   └── workflows/
├── docker-compose.yml
├── .env.example
├── pyproject.toml
├── package.json
└── README.md
```

---

# 12. Downloader Core

CLI и web API должны использовать одно ядро.

```text
CLI ───────────┐
               ├── downloader-core
Web API ───────┘
```

Ядро не должно:

- читать `input()`;
- выводить бизнес-результат через `print()`;
- самостоятельно управлять web-состоянием;
- зависеть от FastAPI;
- зависеть от конкретной очереди задач.

Ядро должно:

- принимать типизированные параметры;
- возвращать типизированный результат;
- сообщать прогресс через callback/event;
- выбрасывать доменные исключения;
- быть покрытым тестами;
- одинаково работать из CLI и worker.

---

# 13. Основные модели данных

## MediaSource

```text
id
url
platform
media_type
external_id
title
author
duration
thumbnail
metadata
created_at
```

## MediaFormat

```text
format_id
container
video_codec
audio_codec
width
height
fps
bitrate
filesize
has_video
has_audio
```

## Job

```text
id
user_id
job_type
status
progress
stage
source_id
input_options
output_metadata
error_code
error_message
created_at
started_at
completed_at
expires_at
```

## OutputFile

```text
id
job_id
storage_key
filename
mime_type
size
checksum
created_at
expires_at
```

---

# 14. API v1

## Анализ

```text
POST /api/v1/media/analyze
```

## Создание задачи

```text
POST /api/v1/jobs
```

## Получение статуса

```text
GET /api/v1/jobs/{job_id}
```

## Прогресс

```text
GET /api/v1/jobs/{job_id}/events
```

Для MVP можно использовать polling, затем Server-Sent Events.

## Отмена

```text
POST /api/v1/jobs/{job_id}/cancel
```

## Повтор

```text
POST /api/v1/jobs/{job_id}/retry
```

## Скачивание результата

```text
GET /api/v1/files/{file_id}/download
```

## Удаление

```text
DELETE /api/v1/files/{file_id}
```

---

# 15. Безопасность

## 15.1. SSRF

Запрещать доступ к:

```text
localhost
127.0.0.0/8
10.0.0.0/8
172.16.0.0/12
192.168.0.0/16
169.254.0.0/16
::1
private IPv6 ranges
cloud metadata endpoints
```

Проверять:

- протокол;
- hostname;
- DNS resolution;
- конечный IP;
- redirect chain;
- повторный DNS resolution после redirect.

## 15.2. Shell injection

Нельзя использовать shell-команды, собранные конкатенацией строк.

Команды FFmpeg и yt-dlp должны запускаться:

- без `shell=True`;
- с массивом аргументов;
- с валидацией входных параметров;
- с ограниченным набором разрешённых опций.

## 15.3. Ограничение ресурсов

Нужны:

- rate limiting;
- максимальный размер;
- максимальная длительность;
- максимальное количество playlist items;
- timeout;
- ограничение CPU;
- ограничение памяти;
- ограничение диска;
- лимит параллельных задач;
- отмена зависших процессов.

## 15.4. Изоляция

- API-контейнер не запускает FFmpeg;
- worker работает с ограниченными правами;
- временное хранилище изолировано;
- файлы получают случайные внутренние имена;
- пользовательское имя используется только при отдаче файла;
- опасные MIME-типы блокируются.

---

# 16. Хранение и жизненный цикл файлов

MVP:

- локальное volume-хранилище;
- TTL результата;
- периодический cleanup job;
- удаление незавершённых файлов;
- контроль свободного диска.

Production:

- S3-compatible storage;
- signed URLs;
- lifecycle policies;
- отдельное temporary storage;
- checksum;
- антивирусная проверка пользовательских файлов при необходимости.

Интерфейс сообщает:

> Файл будет автоматически удалён через определённое время.

---

# 17. SEO-стратегия

SEO строится вокруг пользовательских задач, а не только платформ.

## Группы запросов

### По платформе

- YouTube downloader;
- TikTok downloader;
- Instagram downloader;
- SoundCloud downloader.

### По операции

- extract audio from video;
- cut video online;
- convert video to GIF;
- download subtitles;
- convert WebM to MP4.

### По результату

- MP3;
- MP4;
- GIF;
- SRT;
- WAV;
- FLAC.

### По сценарию

- download part of a video;
- create a reaction GIF;
- save a lecture offline;
- download playlist as MP3.

## Техническое SEO

- SSR/SSG;
- metadata;
- canonical;
- sitemap;
- robots.txt;
- Open Graph;
- hreflang;
- structured data;
- FAQ schema;
- SoftwareApplication schema;
- HowTo schema;
- Core Web Vitals;
- noindex для пользовательских job-страниц.

---

# 18. Юридическое позиционирование

Продукт должен быть представлен как инструмент для:

- собственного контента;
- контента с разрешением;
- public-domain материалов;
- контента, использование которого разрешено законом и правилами источника.

Необходимо подготовить:

- Terms of Use;
- Privacy Policy;
- Copyright Policy;
- DMCA/правообладательскую форму;
- Acceptable Use Policy;
- механизм удаления спорного контента;
- понятное предупреждение перед запуском задачи.

Нельзя обещать:

> Скачать абсолютно всё с любого сайта.

Корректнее:

> Поддерживает большое количество совместимых видео- и аудиоплатформ.

---

# 19. Варианты поставки продукта

## 19.1. Public Web SaaS

Преимущества:

- не требует установки;
- простой вход;
- SEO;
- монетизация.

## 19.2. Self-hosted Community Edition

Запуск:

```bash
docker compose up -d
```

Преимущества:

- файлы остаются у пользователя;
- большие файлы;
- локальная сеть;
- open-source аудитория;
- меньшие инфраструктурные затраты.

## 19.3. Desktop Application

Более поздний этап:

- desktop shell;
- локальный worker;
- web UI;
- отсутствие загрузки файлов на внешний сервер.

## 19.4. API

Для разработчиков и автоматизации:

- analyze;
- download;
- extract;
- cut;
- convert;
- subtitles.

---

# 20. Монетизация

## Free

- ограничение размера;
- ограничение длительности;
- несколько задач;
- стандартная очередь;
- ограниченные playlist operations;
- базовые форматы.

## Pro

- большие файлы;
- высокое качество;
- playlists;
- batch processing;
- расширенные форматы;
- история;
- приоритетная очередь;
- длительное хранение;
- расширенный cutter;
- social presets.

## Self-hosted

- Community Edition;
- Team Edition;
- API;
- custom branding;
- multi-user;
- admin dashboard.

Не использовать агрессивную рекламу, ложные кнопки и принудительные редиректы.

---

# 21. Что входит в MVP

## Обязательно

1. URL Analyzer.
2. Превью и метаданные.
3. Выбор качества.
4. Скачивание видео.
5. Извлечение MP3.
6. Обрезка по времени.
7. Создание GIF.
8. Очередь задач.
9. Прогресс.
10. Отмена задачи.
11. Автоматическая очистка.
12. Безопасная валидация URL.
13. Responsive UI.
14. Отдельные страницы основных инструментов.
15. Базовое SEO.
16. Docker Compose для локального запуска.

## Сразу после MVP

1. Субтитры.
2. Локальные файлы.
3. Playlist selection.
4. Animated WebP и loop video.
5. Social presets.
6. История.
7. Авторизация.
8. S3 storage.
9. Self-hosted documentation.
10. Public API.

## Пока не входит

- полноценный видеоредактор;
- сложный AI-монтаж;
- мобильные приложения;
- browser extension;
- cloud drive;
- team collaboration;
- собственная CDN;
- сотни форматов без востребованного сценария.

---

# 22. Дорожная карта

## Phase 0 — Repository Audit and Cleanup

### Цель

Превратить существующий CLI-репозиторий в чистую и воспроизводимую основу.

### Задачи

- провести аудит текущего кода;
- определить реально работающие сценарии;
- удалить временные копии файлов;
- удалить бинарники FFmpeg из Git;
- добавить `pyproject.toml`;
- зафиксировать зависимости;
- определить поддерживаемую версию Python;
- добавить `.env.example`;
- настроить Ruff;
- настроить mypy;
- настроить pytest;
- настроить pre-commit;
- добавить GitHub Actions;
- обновить README;
- оформить issues и milestones.

### Результат

CLI стабильно запускается из чистого окружения, зависимости воспроизводимы, репозиторий готов к рефакторингу.

---

## Phase 1 — Downloader Core Refactoring

### Цель

Отделить бизнес-логику от терминального интерфейса.

### Задачи

- выделить analyzer;
- выделить video downloader;
- выделить audio extractor;
- выделить playlist downloader;
- выделить cutter;
- создать FFmpeg adapter;
- создать yt-dlp adapter;
- создать модели параметров и результатов;
- создать доменные ошибки;
- добавить progress events;
- добавить unit tests;
- сохранить CLI как отдельный adapter.

### Результат

Одна библиотека обслуживает CLI и будущий worker.

### Definition of Done

- в core нет `input()`;
- в core нет прямых пользовательских `print()`;
- операции вызываются программно;
- ошибки типизированы;
- прогресс доступен через callback;
- критические сценарии покрыты тестами.

---

## Phase 2 — Architecture Foundation

### Цель

Создать базовую инфраструктуру web-приложения.

### Задачи

- создать monorepo;
- создать FastAPI;
- создать Next.js;
- добавить PostgreSQL;
- добавить Redis;
- добавить worker;
- добавить Docker Compose;
- настроить migrations;
- настроить structured logging;
- настроить health checks;
- настроить конфигурацию;
- определить storage abstraction.

### Результат

Frontend, API, worker, database и queue запускаются одной командой.

---

## Phase 3 — Smart URL Analyzer

### Цель

Реализовать главный входной сценарий.

### Задачи

- endpoint анализа;
- URL validation;
- SSRF protection;
- нормализация metadata;
- форматирование duration;
- список доступных форматов;
- thumbnail;
- определение playlist;
- subtitle availability;
- caching;
- error mapping;
- analyzer UI;
- loading, success, empty и error states.

### Результат

Пользователь вставляет ссылку и получает полноценную карточку медиа.

---

## Phase 4 — Job System

### Цель

Перевести длительные операции в фоновые задачи.

### Задачи

- модель Job;
- task queue;
- worker execution;
- progress reporting;
- polling или SSE;
- cancel;
- retry;
- timeout;
- resource limits;
- cleanup;
- failed job diagnostics;
- job UI.

### Результат

Скачивание не блокирует API, прогресс сохраняется и отображается.

---

## Phase 5 — Video and Audio MVP

### Цель

Запустить базовую коммерчески понятную функцию.

### Задачи

- download video;
- quality selection;
- audio extraction;
- MP3 preset;
- format presets;
- estimated filesize;
- result download;
- signed/controlled download URLs;
- filename sanitization;
- automatic expiration.

### Результат

Пользователь может скачать видео или получить аудио.

---

## Phase 6 — Cutter and GIF Maker

### Цель

Добавить сильное отличие от обычных downloader-сервисов.

### Задачи

- start/end validation;
- server-side cut;
- no-reencode mode, где возможно;
- accurate cut mode;
- GIF generation;
- width;
- FPS;
- quality;
- size estimation;
- preview metadata;
- UI для cutter;
- UI для GIF.

### Результат

Пользователь может получить фрагмент и GIF без сторонних сервисов.

---

## Phase 7 — Design System and SaaS UX

### Цель

Создать единый визуальный язык.

### Задачи

- design tokens;
- typography;
- spacing;
- radius;
- shadows;
- neumorphic components;
- form components;
- buttons;
- job cards;
- status badges;
- empty states;
- error states;
- skeletons;
- responsive layout;
- dark mode;
- accessibility audit;
- Storybook.

### Результат

Проект выглядит как современный SaaS, а не как набор несвязанных страниц.

---

## Phase 8 — SEO and Public Launch MVP

### Цель

Подготовить продукт к индексации и первым пользователям.

### Задачи

- landing page;
- tool pages;
- metadata;
- sitemap;
- robots;
- canonical;
- Open Graph;
- structured data;
- FAQ;
- How It Works;
- Supported Sites;
- legal pages;
- analytics;
- Core Web Vitals;
- error monitoring;
- production deployment.

### Результат

MVP доступен публично, индексируется и измеряет ключевые действия пользователей.

---

## Phase 9 — Subtitles and Local Files

### Цель

Расширить проект за пределы простого скачивания.

### Задачи

- subtitle language list;
- SRT;
- VTT;
- TXT;
- local file upload;
- upload progress;
- file validation;
- local cutter;
- local converter;
- local GIF;
- antivirus strategy;
- upload limits.

### Результат

Пользователь может работать как со ссылками, так и со своими файлами.

---

## Phase 10 — Playlist Workspace

### Цель

Сделать плейлисты управляемыми.

### Задачи

- playlist analysis;
- item selection;
- range selection;
- batch jobs;
- aggregate progress;
- numbering;
- ZIP;
- M3U;
- retry one item;
- skip completed;
- limits.

### Результат

Плейлист становится полноценным рабочим процессом, а не одной непрозрачной задачей.

---

## Phase 11 — Social Media Presets

### Цель

Сделать продукт полезным создателям контента.

### Задачи

- aspect ratio presets;
- crop;
- fit;
- blurred background;
- output resolution;
- safe areas;
- loop export;
- subtitles burn-in;
- audio normalization;
- template UI.

### Результат

Пользователь создаёт готовый фрагмент для нужной платформы.

---

## Phase 12 — Accounts, History and Billing

### Цель

Подготовить SaaS-модель.

### Задачи

- authentication;
- user profile;
- history;
- quotas;
- usage tracking;
- plans;
- billing;
- priority queue;
- admin dashboard;
- abuse controls;
- retention settings.

### Результат

Продукт поддерживает бесплатных и платных пользователей.

---

## Phase 13 — Self-hosted Edition

### Цель

Создать отдельную open-source ценность.

### Задачи

- production Docker Compose;
- setup wizard;
- local storage mode;
- configurable limits;
- admin settings;
- backup documentation;
- upgrade documentation;
- releases;
- versioning;
- migration guide.

### Результат

Пользователь может развернуть MegaDownloader на собственном компьютере или сервере.

---

## Phase 14 — Public API and Integrations

### Цель

Открыть продукт для автоматизации.

### Задачи

- API keys;
- scoped permissions;
- rate limits;
- webhooks;
- idempotency;
- usage logs;
- API documentation;
- SDK examples;
- browser extension evaluation;
- integrations.

### Результат

MegaDownloader становится платформой, а не только сайтом.

---

# 23. Приоритеты реализации

## Приоритет P0

Без этого продукт не может работать:

- core refactoring;
- analyzer;
- background jobs;
- video download;
- audio extraction;
- file lifecycle;
- SSRF protection;
- resource limits;
- progress;
- Docker setup.

## Приоритет P1

Формирует отличие продукта:

- cutter;
- GIF;
- subtitles;
- local files;
- playlist selection;
- design system;
- SEO pages.

## Приоритет P2

Рост и монетизация:

- social presets;
- accounts;
- history;
- billing;
- self-hosted release;
- public API.

---

# 24. Ключевые метрики

## Продуктовые

- URL Analyze Success Rate;
- Analyze-to-Job Conversion;
- Job Completion Rate;
- Time to First Result;
- Download Result Rate;
- Repeat Usage;
- Error Rate by Platform;
- Average Queue Time;
- Cancellation Rate.

## Технические

- API latency;
- analyzer latency;
- worker runtime;
- CPU per job;
- disk per job;
- storage cleanup success;
- failure categories;
- retry success;
- uptime.

## SEO

- indexed pages;
- organic impressions;
- organic clicks;
- landing-page conversion;
- Core Web Vitals;
- query groups by intent.

---

# 25. Основные риски

## Изменения платформ

Меры:

- регулярно обновлять yt-dlp;
- иметь automated compatibility checks;
- логировать ошибки по extractor;
- не связывать UI с особенностями одной платформы.

## Высокая стоимость обработки

Меры:

- лимиты;
- очередь;
- filesize estimate;
- short TTL;
- worker autoscaling;
- self-hosted edition.

## Заполнение диска

Меры:

- hard quota;
- cleanup scheduler;
- storage monitoring;
- reject jobs при низком свободном месте.

## Злоупотребления

Меры:

- rate limiting;
- anonymous quotas;
- CAPTCHA при подозрении;
- abuse detection;
- IP/user limits;
- legal reporting flow.

## Сложность UX

Меры:

- Simple Mode;
- presets;
- progressive disclosure;
- one primary action per screen;
- пользовательские названия вместо терминов кодеков.

---

# 26. Definition of Success для первой версии

MVP считается успешным, когда новый пользователь без инструкции может:

1. открыть сайт;
2. вставить поддерживаемую ссылку;
3. увидеть превью и информацию;
4. выбрать Video, Audio, Clip или GIF;
5. запустить задачу;
6. понять текущий статус;
7. получить готовый файл;
8. увидеть срок удаления файла;
9. повторить операцию с другой ссылкой.

Технически:

- обработка выполняется в worker;
- API не блокируется;
- ошибки понятны;
- временные файлы очищаются;
- приватные IP недоступны;
- критические операции покрыты тестами;
- проект запускается через Docker Compose;
- CLI продолжает работать через то же ядро.

---

# 27. Итоговое определение проекта

**MegaDownloader Video & Audio** — это единое web-пространство для получения и обработки онлайн-медиа.

Проект объединяет:

- downloader;
- audio extractor;
- playlist manager;
- video cutter;
- GIF maker;
- subtitle tools;
- media converter;
- social media preparation.

Главное отличие:

> Пользователь анализирует медиа один раз, после чего выполняет все необходимые действия в одном последовательном и понятном интерфейсе.

Технически продукт строится как разделённая система:

- Next.js отвечает за UX и SEO;
- FastAPI отвечает за API и управление задачами;
- Redis и очередь управляют фоновыми операциями;
- worker выполняет yt-dlp и FFmpeg;
- PostgreSQL хранит состояние;
- storage хранит временные результаты;
- downloader-core остаётся общим для CLI, web и self-hosted версий.

Это позволяет сохранить уже созданный терминальный функционал и постепенно превратить его в устойчивый SaaS-продукт.
