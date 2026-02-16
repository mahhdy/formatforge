
# 🔄 FormatForge: ابزار جامع تبدیل اسناد چندفرمتی به MDX

## 0. **Request**
```markdown
حال به من یک پرامپت خوب و کامل و همراه با جزءیات بده که بتوانم ابزاری طراحی کنم در ویندوز این نمونه‌ها و سایر فایل‌هایی از این دست را به درستی در یکی از قالب‌های فایل تکی، تعدادی فایل تکی در یک پوشه، فایل های پراکنده ی مرتبط با یک کتاب داخل یک پوشه، تعدادی فایل زیپ حاوی تک فایل و یا پوشه‌های به هم مرتبط، تک فایل زیپ (سند تک فایلی یا سند چند فایلی داخل یک پوشه) و نظایر آن دریافت کرده و پردازش و تست و خروجی دهی کند. 
پس ۱- ورودی را اسکن کرده و شناسایی کند. (تایید بگیرد)
۲- اطلاعات frontmatter و Metadata   مورد نیاز را بگیرد ویا با  AI   تکمیل کند. به خصوص برای slug و فایل‌هایی که دارای فایل‌های مرتبط و یا نیازمند رسانه‌های مرتبط (عکس و png , svg و ...) هستند. 
۲.۵- تست سریع تبدیل را انجام داده و اگر فایل مشکل دارد پیشنهاد اصلاح بدهد. 
۳- به درستی همه‌ ی انواع ورودی را با در اختیار قرار دادن انتخاب هایی برای تبدیل درست و کامل (همراه نمایش پیشرفت کار و خطاهای احتمالی و توصیه‌های تصحیح و تبدیل درست) به خروجی مناسب برای وب سایت من MDX تبدیل کرده و همه ی فایل‌ها و سندهای مرتبط را با ارتباط و پیوند دادن صحیح نهایی کند.
۴- تست خروجی و درتس بودن تبدیل‌ها و کامل بودن فایل را انجام دهد. 
۵- خروجی را در محلی که تعیین کرده‌ام یا انتخاب کنم منتقل کند. (با تمامی اجزا و ابعاد مورد نیاز) 
۶- گزارش موفقیت را در یک فایل مرکزی حفظ و نگهداری کند. 

یا اگر پیشنهاد بهتری داری بده. امیدوارم ایده را به خوبی بگیری. 
این پرامپت باید همه‌ی اجزا و نیازمندی‌های تبدیل درست و جامع را داشته باشد و نکته‌های فنی به خصوص در خصوص ملاحظات زبان فارسی و متون دو زبانه را در انواع فرمت‌های ورودی در نظر بگیرد. 
ممنون
```

## ۱. شناسنامه پروژه

**نام پروژه:** FormatForge (یا نام دلخواه)
**پلتفرم هدف:** Windows 10/11 (x64)
**زبان(های) توسعه:** Python 3.11+ به‌عنوان هسته اصلی، PowerShell 7+ برای اسکریپت‌های سیستمی، و اختیاراً Rust/Go برای ماژول‌های عملکرد-بحرانی
**رابط کاربری:** 
  - CLI اصلی (اولویت اول — کامل و قابل اسکریپت)
  - TUI با Rich/Textual (اولویت دوم — تجربه بهتر در ترمینال)
  - GUI با Tauri یا Electron (اولویت سوم — اختیاری)
**زبان محتوا:** فارسی (RTL) به‌عنوان زبان اصلی، با پشتیبانی کامل از محتوای دوزبانه فارسی-انگلیسی و متون تمام‌انگلیسی
**خروجی نهایی:** فایل(های) MDX سازگار با Next.js / Astro / Gatsby / Docusaurus یا هر فریم‌ورک مبتنی بر MDX

---

## ۲. بیان مسئله و هدف

من یک مجموعه بزرگ از مقالات، کتاب‌ها، بیانیه‌ها و اثبات‌های منطقی ریاضی دارم که در فرمت‌های مختلف (LaTeX, HTML, Markdown, DOCX, PDF, RST, AsciiDoc, EPUB, Jupyter Notebook) نوشته شده‌اند. می‌خواهم ابزاری طراحی کنم که:

1. **ورودی‌های متنوع** را با هر ساختاری (تک‌فایل، پوشه، ZIP، ترکیبی) دریافت و شناسایی کند
2. **متادیتا و frontmatter** را استخراج، تکمیل و اعتبارسنجی کند (با کمک AI در صورت نیاز)
3. **تبدیل دقیق و کامل** به MDX انجام دهد با حفظ تمام عناصر (ریاضی، نمودار، کد، تصویر، جدول، ارجاعات، RTL، نیم‌فاصله و...)
4. **تست کیفیت** خروجی را به‌صورت خودکار انجام دهد
5. **خروجی نهایی** را در ساختار مناسب وب‌سایت من مستقر کند
6. **گزارش مرکزی** از تمام تبدیل‌ها نگهداری کند

### ویژگی‌های کلیدی محتوای من:
- اکثراً **فارسی با اصطلاحات انگلیسی** درون متن
- شامل **فرمول‌های ریاضی پیچیده** (ماتریس، aligned، cases، اثبات‌های چندمرحله‌ای)
- شامل **نمودارهای متنوع** (TikZ، pgfplots، Mermaid، SVG)
- شامل **کد برنامه‌نویسی** با syntax highlighting
- شامل **جداول پیچیده** (ادغامی، رنگی، طولانی، افقی)
- شامل **ارجاعات متقاطع** و کتاب‌نامه
- نیاز به **حفظ نیم‌فاصله** (ZWNJ, U+200C) در تمام مراحل
- نیاز به **جهت‌دهی دوگانه** (RTL برای فارسی، LTR برای کد/ریاضی/انگلیسی)

---

## ۳. معماری کلی سیستم

### ۳.۱ خط لوله پردازش (Processing Pipeline)

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌──────────────┐
│  STAGE 1    │───▶│  STAGE 2    │───▶│  STAGE 2.5  │───▶│  STAGE 3     │
│  اسکن و    │    │  متادیتا و  │    │  تست سریع   │    │  تبدیل اصلی │
│  شناسایی    │    │ frontmatter │    │  و پیش‌بررسی │    │  به MDX      │
└─────────────┘    └─────────────┘    └─────────────┘    └──────┬───────┘
                                                                │
┌─────────────┐    ┌─────────────┐    ┌──────────────┐          │
│  STAGE 6    │◀───│  STAGE 5    │◀───│  STAGE 4     │◀─────────┘
│  گزارش     │    │  استقرار    │    │  تست کیفیت   │
│  مرکزی     │    │  خروجی      │    │  خروجی       │
└─────────────┘    └─────────────┘    └──────────────┘
```

### ۳.۲ ساختار ماژولار

```
formatforge/
├── cli/                      # رابط خط فرمان
│   ├── __main__.py
│   ├── commands/
│   │   ├── scan.py           # دستور اسکن
│   │   ├── convert.py        # دستور تبدیل
│   │   ├── test.py           # دستور تست
│   │   ├── deploy.py         # دستور استقرار
│   │   └── report.py         # دستور گزارش
│   └── interactive.py        # حالت تعاملی
│
├── core/                     # هسته اصلی
│   ├── scanner/              # اسکنر ورودی
│   │   ├── file_detector.py  # تشخیص نوع فایل
│   │   ├── structure_analyzer.py  # تحلیل ساختار
│   │   ├── archive_handler.py     # مدیریت ZIP/RAR
│   │   └── encoding_detector.py   # تشخیص encoding
│   │
│   ├── metadata/             # مدیریت متادیتا
│   │   ├── extractor.py      # استخراج متادیتا
│   │   ├── schema.py         # شِمای متادیتا
│   │   ├── slug_generator.py # تولید slug
│   │   ├── ai_completer.py   # تکمیل با AI
│   │   └── validator.py      # اعتبارسنجی
│   │
│   ├── converters/           # تبدیل‌گرها
│   │   ├── base.py           # کلاس پایه
│   │   ├── latex_to_mdx.py
│   │   ├── html_to_mdx.py
│   │   ├── md_to_mdx.py
│   │   ├── docx_to_mdx.py
│   │   ├── pdf_to_mdx.py
│   │   ├── rst_to_mdx.py
│   │   ├── asciidoc_to_mdx.py
│   │   ├── epub_to_mdx.py
│   │   └── notebook_to_mdx.py
│   │
│   ├── processors/           # پردازشگرهای تخصصی
│   │   ├── math_processor.py       # فرمول‌های ریاضی
│   │   ├── mermaid_processor.py    # نمودارهای Mermaid
│   │   ├── tikz_processor.py      # تبدیل TikZ به SVG/تصویر
│   │   ├── code_processor.py      # بلوک‌های کد
│   │   ├── table_processor.py     # جداول پیچیده
│   │   ├── image_processor.py     # تصاویر و رسانه
│   │   ├── link_processor.py      # لینک‌ها و ارجاعات
│   │   ├── bibliography_processor.py  # کتاب‌نامه
│   │   ├── footnote_processor.py  # پانوشت
│   │   └── rtl_processor.py       # پردازش RTL/فارسی
│   │
│   ├── persian/              # ماژول تخصصی فارسی
│   │   ├── zwnj_handler.py   # مدیریت نیم‌فاصله
│   │   ├── bidi_handler.py   # مدیریت دوجهتی
│   │   ├── numeral_handler.py # تبدیل اعداد فا↔en
│   │   ├── font_handler.py   # مدیریت فونت
│   │   └── typography.py     # قواعد تایپوگرافی فارسی
│   │
│   ├── quality/              # تست کیفیت
│   │   ├── structural_test.py    # تست ساختاری
│   │   ├── math_test.py          # تست ریاضی
│   │   ├── visual_test.py        # تست بصری
│   │   ├── link_test.py          # تست لینک‌ها
│   │   ├── encoding_test.py      # تست encoding
│   │   ├── rtl_test.py           # تست RTL
│   │   ├── completeness_test.py  # تست کامل بودن
│   │   └── render_test.py        # تست رندر (headless browser)
│   │
│   └── deployer/             # استقرار خروجی
│       ├── file_organizer.py # سازماندهی فایل‌ها
│       ├── asset_manager.py  # مدیریت asset ها
│       └── deployer.py       # انتقال نهایی
│
├── ai/                       # ماژول هوش مصنوعی
│   ├── provider.py           # رابط با API های AI
│   ├── metadata_ai.py        # تکمیل متادیتا
│   ├── content_ai.py         # اصلاح محتوا
│   └── suggestion_ai.py      # پیشنهادات
│
├── reports/                  # گزارش‌دهی
│   ├── report_engine.py
│   ├── templates/
│   └── central_log.py
│
├── config/                   # تنظیمات
│   ├── default_config.yaml
│   ├── user_config.yaml
│   └── website_config.yaml
│
├── templates/                # قالب‌های MDX
│   ├── article.mdx.j2
│   ├── book_chapter.mdx.j2
│   ├── proof.mdx.j2
│   └── components/
│       ├── Theorem.jsx
│       ├── Definition.jsx
│       ├── Proof.jsx
│       ├── Admonition.jsx
│       └── MermaidDiagram.jsx
│
└── tests/                    # تست‌های واحد
    ├── test_files/           # فایل‌های نمونه تست
    └── ...
```

---

## ۴. مشخصات دقیق هر مرحله (Stage)

### ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
### STAGE 1: اسکن و شناسایی ورودی
### ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

#### ۴.۱.۱ انواع ورودی‌های پشتیبانی‌شده

ابزار باید **تمامی** سناریوهای ورودی زیر را پشتیبانی کند:

| سناریو | مثال | توضیح |
|:--------|:------|:------|
| **تک‌فایل** | `article.tex` | یک فایل منفرد |
| **چند فایل تکی در یک پوشه** | `articles/*.tex` | مجموعه مقالات مستقل |
| **فایل‌های مرتبط در یک پوشه** | `book/ch01.tex, ch02.tex, main.tex, refs.bib, images/` | یک کتاب چندفصلی |
| **پوشه‌ی پروژه LaTeX** | `project/` شامل `.tex`, `.bib`, `.sty`, `figures/` | پروژه LaTeX کامل |
| **تک فایل ZIP (سند تکی)** | `article.zip` → `article.tex` | فایل فشرده حاوی یک سند |
| **تک فایل ZIP (سند چندبخشی)** | `book.zip` → `book/ch01.tex, ch02.tex, ...` | فایل فشرده حاوی پروژه |
| **چند فایل ZIP** | `pack1.zip, pack2.zip` | چند آرشیو مرتبط |
| **ترکیبی** | پوشه شامل `.tex`, `.md`, `.html`, `.zip` | ترکیب انواع مختلف |
| **URL** | `https://arxiv.org/abs/...` | دانلود و تبدیل (اختیاری) |
| **Clipboard** | محتوای کپی‌شده | تبدیل مستقیم از clipboard |

#### ۴.۱.۲ الگوریتم شناسایی

```
برای هر ورودی (مسیر، فایل، URL):
│
├─ اگر ZIP/RAR/7Z/TAR.GZ است:
│   ├─ استخراج به پوشه موقت
│   ├─ تحلیل محتوای استخراج‌شده (بازگشتی)
│   └─ تشخیص: «تک‌سند» یا «چندسند» یا «پروژه»
│
├─ اگر پوشه است:
│   ├─ اسکن بازگشتی تمام فایل‌ها
│   ├─ دسته‌بندی بر اساس نوع:
│   │   ├─ اسناد اصلی (.tex, .md, .html, .docx, .pdf, .rst, .adoc, .ipynb, .epub)
│   │   ├─ رسانه‌ها (.png, .jpg, .svg, .gif, .mp4, .mp3, .webp)
│   │   ├─ سبک‌ها (.css, .sty, .cls)
│   │   ├─ متادیتا (.bib, .json, .yaml, .toml)
│   │   └─ سایر
│   ├─ تشخیص ارتباط بین فایل‌ها:
│   │   ├─ تحلیل \input, \include, \bibliography در LaTeX
│   │   ├─ تحلیل لینک‌ها و import ها در MD/HTML
│   │   ├─ تحلیل ارجاعات تصویر (src, \includegraphics, ![])
│   │   └─ ساخت گراف وابستگی
│   └─ تعیین ساختار: «مقالات مستقل» یا «کتاب چندفصلی» یا «مجموعه مرتبط»
│
├─ اگر تک‌فایل است:
│   ├─ تشخیص فرمت (بر اساس پسوند + تحلیل محتوا + magic bytes)
│   ├─ تشخیص encoding (UTF-8/UTF-8 BOM/UTF-16/Windows-1256/ISO-8859-6)
│   ├─ تشخیص زبان (فارسی/انگلیسی/دوزبانه)
│   └─ استخراج متادیتای سریع
│
└─ تولید «گزارش اسکن» (ScanReport)
```

#### ۴.۱.۳ خروجی مرحله ۱: ScanReport

```yaml
# مثال ScanReport
scan_id: "scan_20250713_153042"
timestamp: "2025-07-13T15:30:42+03:30"
input_path: "C:/Users/ali/Documents/logic-book/"
input_type: "directory"     # file | directory | archive | url | clipboard
total_files: 23
structure: "multi_chapter_book"  # single_doc | independent_articles |
                                 # multi_chapter_book | related_collection

documents:
  - id: "doc_001"
    path: "main.tex"
    format: "latex"
    encoding: "utf-8-bom"
    language: "fa+en"        # fa | en | fa+en
    role: "main_entry"       # main_entry | chapter | appendix | standalone
    size_bytes: 45200
    estimated_pages: 12
    dependencies:
      - "chapter01.tex"
      - "chapter02.tex"
      - "references.bib"
    images_referenced:
      - "figures/diagram1.png"
      - "figures/proof-tree.svg"
    has_math: true
    has_code: true
    has_tables: true
    has_bibliography: true
    has_tikz: true

  - id: "doc_002"
    path: "chapter01.tex"
    format: "latex"
    encoding: "utf-8"        # ⚠ بدون BOM
    language: "fa+en"
    role: "chapter"
    parent: "doc_001"
    # ...

assets:
  - path: "figures/diagram1.png"
    type: "image/png"
    size_bytes: 125400
    referenced_by: ["doc_001", "doc_002"]
  - path: "figures/proof-tree.svg"
    type: "image/svg+xml"
    size_bytes: 8900
    referenced_by: ["doc_001"]
  - path: "references.bib"
    type: "bibliography"
    entries_count: 15

warnings:
  - level: "warning"
    file: "chapter01.tex"
    message: "فایل بدون BOM است. ممکن است نیم‌فاصله‌ها از دست بروند."
    suggestion: "تبدیل به UTF-8 with BOM"
  - level: "info"
    file: "figures/old-diagram.png"
    message: "این تصویر در هیچ سندی ارجاع داده نشده."
    suggestion: "حذف یا بررسی"

confirmation_required: true
confirmation_prompt: |
  📂 ساختار شناسایی‌شده:
  ━━━━━━━━━━━━━━━━━━━━
  نوع: کتاب چندفصلی (۲ فصل + مقدمه + کتاب‌نامه)
  فرمت اصلی: LaTeX
  زبان: فارسی-انگلیسی
  ۲ تصویر، ۱ فایل کتاب‌نامه
  ⚠ ۱ هشدار encoding

  آیا این تشخیص صحیح است؟ [بله/خیر/ویرایش]
```

#### ۴.۱.۴ تعامل با کاربر (تأیید)

```
🔍 اسکن ورودی: D:\Code\Apps\formatforge\docs\

📊 نتیجه اسکن:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  نوع ساختار:    📚 کتاب چندفصلی
  فرمت اصلی:     📄 LaTeX
  زبان:          🌐 فارسی + انگلیسی
  encoding:      ✅ UTF-8 (۱ فایل بدون BOM ⚠)
  فایل‌ها:       ۴ سند + ۲ تصویر + ۱ کتاب‌نامه

  📄 main.tex ────────── نقطه ورود اصلی
    ├── chapter01.tex ── فصل ۱: مقدمه و مفاهیم
    ├── chapter02.tex ── فصل ۲: منطق گزاره‌ای
    ├── references.bib ─ کتاب‌نامه (۱۵ مرجع)
    └── figures/
        ├── diagram1.png  (122 KB)
        └── proof-tree.svg (9 KB)

  ⚠ هشدارها:
    1. chapter01.tex: بدون BOM → پیشنهاد: تبدیل encoding

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  [T] تأیید و ادامه
  [E] ویرایش ساختار
  [F] اصلاح خودکار هشدارها
  [A] تأیید + اصلاح خودکار
  [Q] لغو

  انتخاب شما: █
```

---

### ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
### STAGE 2: استخراج و تکمیل متادیتا و Frontmatter
### ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

#### ۴.۲.۱ شِمای متادیتا (Metadata Schema)

```typescript
// شِمای کامل متادیتای هر سند
interface DocumentMetadata {
  // --- اجباری ---
  title: string;                    // عنوان فارسی
  titleEn?: string;                 // عنوان انگلیسی (اختیاری)
  slug: string;                     // مسیر URL (فقط حروف لاتین، عدد، خط‌تیره)
  date: string;                     // تاریخ انتشار (ISO 8601)
  lang: "fa" | "en" | "fa-en";     // زبان اصلی
  dir: "rtl" | "ltr";              // جهت اصلی

  // --- نویسنده ---
  author: {
    name: string;
    nameEn?: string;
    email?: string;
    url?: string;
    affiliation?: string;
  };

  // --- دسته‌بندی ---
  type: "article" | "book" | "chapter" | "proof" | "lecture-note" | "tutorial";
  tags: string[];                   // برچسب‌ها (فارسی)
  tagsEn?: string[];                // برچسب‌ها (انگلیسی)
  categories: string[];             // دسته‌بندی‌ها
  series?: {                        // اگر بخشی از یک مجموعه باشد
    name: string;
    order: number;
    total?: number;
  };

  // --- محتوا ---
  description: string;              // خلاصه (فارسی، حداکثر ۳۰۰ کاراکتر)
  descriptionEn?: string;           // خلاصه انگلیسی
  abstract?: string;                // چکیده مفصل
  keywords: string[];               // کلمات کلیدی
  toc: boolean;                     // نمایش فهرست مطالب
  math: boolean;                    // آیا شامل ریاضی است
  mermaid: boolean;                 // آیا شامل نمودار Mermaid است
  codeHighlight: boolean;           // آیا شامل کد است

  // --- فایل‌ها ---
  sourceFormat: string;             // فرمت اصلی (latex, html, md, ...)
  sourceFile: string;               // نام فایل اصلی
  assets: {                         // فایل‌های وابسته
    images: string[];
    files: string[];
  };
  featuredImage?: string;           // تصویر شاخص

  // --- SEO و وب ---
  canonical?: string;               // URL کانونیکال
  noindex?: boolean;                // عدم ایندکس
  ogImage?: string;                 // تصویر Open Graph

  // --- تبدیل ---
  convertedAt: string;              // زمان تبدیل
  converterVersion: string;         // نسخه ابزار تبدیل
  qualityScore: number;             // امتیاز کیفیت (0-100)
  conversionNotes?: string[];       // یادداشت‌های تبدیل
}
```

#### ۴.۲.۲ استخراج متادیتا از فرمت‌های مختلف

```
فرمت         │  منابع استخراج متادیتا
━━━━━━━━━━━━━┿━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LaTeX        │  \title{}, \author{}, \date{}, \begin{abstract}
             │  پکیج hyperref: \hypersetup{pdftitle=...}
             │  کامنت‌های سرفایل (% Title: ...)
             │  فایل .bib برای کتاب‌نامه
━━━━━━━━━━━━━┿━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HTML         │  <title>, <meta name="...">, <meta property="og:...">
             │  Open Graph tags, Schema.org, Dublin Core
             │  <h1> اولین عنوان
━━━━━━━━━━━━━┿━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Markdown     │  YAML frontmatter (---)
             │  TOML frontmatter (+++)
             │  اولین H1 (#)
━━━━━━━━━━━━━┿━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DOCX         │  Core Properties (title, author, subject, keywords)
             │  Custom Properties
             │  اولین پاراگراف با سبک Heading 1
━━━━━━━━━━━━━┿━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PDF          │  PDF metadata (Title, Author, Subject, Keywords)
             │  XMP metadata
             │  اولین خط بزرگ (عنوان احتمالی)
━━━━━━━━━━━━━┿━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RST          │  عنوان اصلی (overline + underline)
             │  :field: مقادیر
             │  .. meta:: directives
━━━━━━━━━━━━━┿━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AsciiDoc     │  = عنوان سطح ۰
             │  :attribute: مقادیر
━━━━━━━━━━━━━┿━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Jupyter NB   │  metadata.kernelspec, metadata.title
             │  اولین سلول Markdown
```

#### ۴.۲.۳ تولید Slug

```python
# قواعد تولید slug:
# 1. اگر عنوان انگلیسی وجود دارد → از آن استفاده کن
# 2. اگر فقط فارسی است → ترجمه AI یا transliterate
# 3. slug فقط شامل: [a-z0-9-]
# 4. حداکثر ۶۰ کاراکتر
# 5. بدون خط‌تیره تکراری یا ابتدایی/انتهایی
# 6. یکتا بودن در سایت (بررسی با گزارش مرکزی)

# مثال‌ها:
# "قانون دمورگان" → "de-morgans-laws"
# "مبانی منطق ریاضی — فصل ۱" → "foundations-mathematical-logic-ch1"
# "Proof of Completeness Theorem" → "proof-completeness-theorem"

# برای کتاب چندفصلی:
# series_slug/chapter_slug
# "logic-foundations/ch01-introduction"
# "logic-foundations/ch02-propositional-logic"
```

#### ۴.۲.۴ تکمیل با AI

```
فیلدهایی که AI می‌تواند تکمیل یا پیشنهاد دهد:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. description / descriptionEn
   → خلاصه‌سازی خودکار محتوا

2. tags / tagsEn / keywords
   → استخراج کلمات کلیدی از محتوا

3. titleEn (اگر عنوان فقط فارسی باشد)
   → ترجمه عنوان

4. slug
   → تولید slug مناسب از عنوان

5. categories
   → دسته‌بندی خودکار بر اساس محتوا

6. featuredImage description / alt text
   → توصیف تصاویر

7. series detection
   → تشخیص اینکه آیا سند بخشی از یک مجموعه است

API‌های پشتیبانی‌شده:
  - OpenAI GPT-4 / GPT-4o
  - Anthropic Claude
  - Google Gemini
  - Local LLM (Ollama / LM Studio)
  - هیچ‌کدام (تکمیل دستی توسط کاربر)
```

#### ۴.۲.۵ تعامل با کاربر

```
📋 متادیتای استخراج‌شده:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  عنوان:     ✅ مبانی منطق ریاضی و اثبات‌های صوری
  عنوان EN:  🤖 Foundations of Mathematical Logic and Formal Proofs
  slug:      🤖 foundations-mathematical-logic-formal-proofs
  نویسنده:  ✅ مهدی سالم
  تاریخ:    ✅ 2025-07-13
  زبان:     ✅ فارسی + انگلیسی (fa-en)
  نوع:      🤖 book (کتاب)
  خلاصه:    🤖 «این کتاب به بررسی مبانی منطق ریاضی...» (۱۴۵ کاراکتر)
  برچسب‌ها:  🤖 [منطق, ریاضی, دمورگان, اثبات, گزاره‌ای]
  ریاضی:    ✅ بله
  Mermaid:   ❌ خیر
  کد:       ✅ بله

  ✅ = استخراج‌شده از سند
  🤖 = پیشنهاد AI
  ❓ = ناشناخته — نیاز به ورود دستی

  [C] تأیید همه
  [E] ویرایش (شماره فیلد)
  [R] بازتولید پیشنهادات AI
  [Q] لغو

  انتخاب شما: █
```

---

### ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
### STAGE 2.5: تست سریع و پیش‌بررسی
### ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

#### ۴.۲.۵.۱ بررسی‌های پیش از تبدیل

```
بررسی‌های فوری (Fast Checks):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[الف] بررسی encoding:
  ☐ آیا UTF-8 است؟
  ☐ آیا BOM دارد؟
  ☐ آیا نیم‌فاصله‌ها سالم هستند؟ (شمارش ZWNJ)
  ☐ آیا کاراکترهای عجیب/شکسته وجود دارد؟

[ب] بررسی ساختار فایل:
  ☐ LaTeX: آیا \begin{document} و \end{document} وجود دارد؟
  ☐ LaTeX: آیا پکیج‌ها تعارض ندارند؟ (بررسی لیست تعارضات شناخته‌شده)
  ☐ LaTeX: آیا xepersian آخرین پکیج است؟
  ☐ HTML: آیا well-formed است؟ (تگ‌های بسته‌نشده)
  ☐ Markdown: آیا frontmatter معتبر YAML/TOML است؟
  ☐ DOCX: آیا فایل corrupt نیست؟
  ☐ PDF: آیا قابل خواندن/extractable است؟

[ج] بررسی وابستگی‌ها:
  ☐ آیا تمام تصاویر ارجاع‌شده وجود دارند؟
  ☐ آیا تمام فایل‌های include/input وجود دارند؟
  ☐ آیا فایل .bib وجود دارد (اگر ارجاع شده)؟
  ☐ آیا فونت‌های مورد نیاز نصب هستند؟ (برای LaTeX)

[د] بررسی محتوا:
  ☐ آیا فرمول‌های ریاضی syntax صحیحی دارند؟
    → تست سریع: parse فرمول‌ها با KaTeX/regex
  ☐ آیا بلوک‌های کد syntax صحیحی دارند؟
  ☐ آیا جداول ساختار صحیحی دارند؟
  ☐ آیا لینک‌ها معتبرند؟ (format check, not HTTP check)

[ه] تبدیل آزمایشی:
  ☐ تبدیل ۱۰٪ اول سند (یا اولین فصل)
  ☐ بررسی خروجی آزمایشی
  ☐ تخمین زمان تبدیل کامل
  ☐ شناسایی عناصر پیچیده/مشکل‌ساز
```

#### ۴.۲.۵.۲ گزارش پیش‌بررسی

```
⚡ تست سریع (Pre-flight Check):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ✅ Encoding: UTF-8 BOM
  ✅ ساختار: معتبر
  ✅ وابستگی‌ها: ۲/۲ تصویر موجود، ۱/۱ bib موجود
  ⚠️ ریاضی: ۴۲ فرمول شناسایی شد — ۱ فرمول مشکوک:
     خط ۱۵۷: \begin{align} بدون \end{align} متناظر
     → پیشنهاد: بررسی خط ۱۵۷ فایل chapter02.tex
  ✅ جداول: ۵ جدول — همه معتبر
  ⚠️ TikZ: ۳ نمودار TikZ شناسایی شد
     → این نمودارها به SVG/PNG تبدیل خواهند شد
     → نیاز به نصب: xelatex + dvisvgm (یافت شد ✅)
  ✅ کد: ۴ بلوک کد — زبان‌ها: Python(2), JS(1), LaTeX(1)
  ❌ لینک شکسته: figures/old-diagram.png در خط ۸۹ ارجاع شده
     اما فایل وجود ندارد.
     → پیشنهاد: حذف ارجاع یا تهیه فایل

  📊 تخمین:
  ━━━━━━━━━
  زمان تبدیل: ~۴۵ ثانیه
  حجم خروجی: ~۱۲۰ KB (MDX) + ~۳۵۰ KB (assets)
  امتیاز آمادگی: ۸۵/۱۰۰

  [P] ادامه با تبدیل کامل
  [F] اصلاح خودکار مشکلات قابل‌حل
  [I] نادیده‌گرفتن هشدارها و ادامه
  [Q] لغو و بازگشت

  انتخاب شما: █
```

---

### ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
### STAGE 3: تبدیل اصلی به MDX
### ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

#### ۴.۳.۱ قواعد تبدیل عمومی (تمام فرمت‌ها)

##### الف) ریاضیات

```
ورودی                           │  خروجی MDX
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┿━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LaTeX: $...$ / \(...\)          │  $...$  (KaTeX inline)
LaTeX: $$...$$ / \[...\]       │  $$...$$ (KaTeX display)
LaTeX: \begin{equation}        │  $$...$$ با label
LaTeX: \begin{align}           │  $$\begin{aligned}...$$
LaTeX: \begin{cases}           │  $$\begin{cases}...$$
LaTeX: \begin{pmatrix}         │  $$\begin{pmatrix}...$$
HTML: MathML                    │  $...$ (تبدیل MathML→LaTeX)
HTML: MathJax spans             │  $...$
RST: :math:`...`               │  $...$
RST: .. math::                 │  $$...$$
AsciiDoc: stem:[...]           │  $...$
AsciiDoc: [stem]++++           │  $$...$$

⚠ نکات فارسی:
- متن فارسی درون فرمول: \text{اگر} → حفظ شود
- ترتیب RTL: فرمول‌ها همیشه LTR رندر می‌شوند
- \label{} → id برای ارجاع متقاطع
- \ref{} / \cref{} → لینک داخلی MDX
```

##### ب) نمودارها

```
ورودی                           │  خروجی MDX
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┿━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LaTeX TikZ                      │  گزینه ۱: تبدیل به SVG (dvisvgm)
                                │  گزینه ۲: تبدیل به PNG (ImageMagick)
                                │  گزینه ۳: <MermaidDiagram> اگر قابل تبدیل
LaTeX pgfplots                  │  تبدیل به SVG/PNG
Markdown ```mermaid             │  <MermaidDiagram chart={`...`} />
HTML <div class="mermaid">      │  <MermaidDiagram chart={`...`} />
SVG درون‌خطی                     │  فایل .svg جداگانه + <Image>
                                │  یا حفظ inline SVG
```

##### ج) جداول

```
ورودی                           │  خروجی MDX
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┿━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ساده (بدون ادغام)               │  Markdown pipe table
ادغامی (colspan/rowspan)        │  <table> HTML درون MDX
رنگی                           │  <table> با className → CSS
طولانی (longtable)              │  <div style="overflow-x:auto"><table>
افقی (sidewaystable)            │  <div className="landscape-table">
tabularx                        │  <table> با عرض ۱۰۰٪
CSV table                       │  Markdown pipe table

⚠ نکات فارسی:
- جهت جدول: direction: rtl
- محتوای ریاضی در سلول: حفظ $...$
- header فارسی: text-align: right
- عنوان جدول (caption): زیر جدول (طبق سنت فارسی)
  یا بالای جدول (طبق سنت انگلیسی) → قابل تنظیم
```

##### د) تصاویر و رسانه

```
ورودی                           │  خروجی MDX
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┿━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
\includegraphics{path}          │  <Image src="path" alt="..." />
![alt](path)                    │  <Image src="path" alt="..." />
<img src="path">                │  <Image src="path" alt="..." />
\begin{figure}...\caption       │  <Figure> کامپوننت
\begin{wrapfigure}              │  <Figure float="right"> یا CSS
\begin{subfigure}               │  <FigureGrid> کامپوننت
<video>/<iframe>                │  <Video> / <Embed> کامپوننت
<audio>                         │  <Audio> کامپوننت
SVG inline                      │  فایل مجزا یا inline

مسیردهی:
- تصاویر کپی می‌شوند به: assets/images/{slug}/
- نام‌گذاری: {slug}-fig-{number}.{ext}
- بهینه‌سازی: WebP/AVIF برای تصاویر رستری
- SVG: بهینه‌سازی با SVGO
- alt text: اجباری (از caption یا AI)
```

##### ه) قضیه / تعریف / اثبات

```
ورودی                           │  خروجی MDX
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┿━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LaTeX: \begin{theorem}          │  <Theorem id="..." title="...">
LaTeX: \begin{definition}       │  <Definition id="..." title="...">
LaTeX: \begin{proof}            │  <Proof for="...">
LaTeX: \begin{example}          │  <Example id="..." title="...">
LaTeX: \begin{lemma}            │  <Theorem type="lemma" ...>
LaTeX: \begin{corollary}        │  <Theorem type="corollary" ...>
tcolorbox (custom)              │  کامپوننت متناظر
Admonition (MD/RST/AsciiDoc)   │  <Admonition type="note|warning|...">

MD: > [!NOTE]                   │  <Admonition type="note">
MD: > [!WARNING]                │  <Admonition type="warning">
MD: > [!TIP]                    │  <Admonition type="tip">
```

##### و) کد

```
ورودی                           │  خروجی MDX
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┿━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LaTeX: \begin{lstlisting}       │  ```python {title="...",lines=true}
LaTeX: \begin{minted}           │  ```python {title="..."}
LaTeX: \begin{verbatim}         │  ```text
MD: ```python                   │  ```python
HTML: <pre><code>               │  ```language
MD: `inline`                    │  `inline`
LaTeX: \texttt{...}             │  `...`
LaTeX: \verb|...|               │  `...`

⚠ جهت: بلوک‌های کد همیشه LTR
   direction: ltr; text-align: left; unicode-bidi: isolate;
```

##### ز) لینک‌ها و ارجاعات

```
ورودی                           │  خروجی MDX
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┿━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
\href{url}{text}                │  [text](url)
\url{url}                       │  [url](url)
\ref{label}                     │  [شماره](#label) یا <InternalRef>
\cref{label}                    │  <CrossRef id="label" />
\cite{key}                      │  <Citation id="key" /> یا [^cite-key]
\footnote{text}                 │  [^fn-N] ... [^fn-N]: text
\endnote{text}                  │  جمع‌آوری در انتهای سند
[text](url)                     │  [text](url) (حفظ)
<a href="url">                  │  [text](url)

⚠ ارجاعات بین فصل‌ها:
  - \ref{ch2:thm:demorgan} →
    [قضیه ۱.۱](/series-slug/ch02#thm-demorgan)
  - لینک‌های نسبی بین فایل‌های MDX
```

##### ح) پانوشت و کتاب‌نامه

```
پانوشت:
━━━━━━
LaTeX \footnote{text}     → [^fn-1] ... [^fn-1]: text
LaTeX \LTRfootnote{text}  → [^fn-1] ... [^fn-1]: text (LTR)
LaTeX \endnote{text}      → جمع‌آوری در بخش «پی‌نوشت‌ها»
MD [^1]                   → حفظ
HTML <sup><a href="#fn">  → [^fn-N]

کتاب‌نامه:
━━━━━━━━━
LaTeX biblatex/bibtex     → تبدیل .bib به JSON
                          → رندر با <Bibliography> کامپوننت
                          → یا تبدیل به لیست مرتب MD
APA/IEEE/... سبک         → قابل تنظیم
ارجاع \cite{key}         → [نویسنده, سال] با لینک به entry
```

##### ط) مدیریت RTL و فارسی

```markdown
قواعد حیاتی RTL/فارسی:
━━━━━━━━━━━━━━━━━━━━━━━

1. نیم‌فاصله (ZWNJ, U+200C):
   - هرگز حذف نشود
   - در هر مرحله تبدیل بررسی شود
   - شمارش ZWNJ قبل و بعد تبدیل: باید برابر باشد
   - اگر اختلاف > 0: هشدار + گزارش محل حذف

2. جهت‌دهی:
   - بدنه اصلی: dir="rtl"
   - بلوک‌های کد: dir="ltr", unicode-bidi: isolate
   - فرمول‌های ریاضی: LTR (خودکار)
   - نمودارهای Mermaid: LTR container, RTL text labels
   - جداول: dir="rtl"
   - بلوک‌های تمام‌انگلیسی: <div dir="ltr" lang="en">

3. گیومه:
   - فارسی: «...»  (U+00AB, U+00BB)
   - نه "..." یا '...'

4. اعداد:
   - متن فارسی: ۰۱۲۳۴۵۶۷۸۹ (اختیاری — قابل تنظیم)
   - کد/ریاضی: 0123456789 (همیشه لاتین)
   - تاریخ فارسی: ۱۴۰۴/۰۴/۲۲

5. تایپوگرافی:
   - فاصله قبل از «:» و «؛» و «?» و «!» → حذف (طبق سنت فارسی)
   - فاصله بعد از «.» و «,» → حفظ
   - می‌ + فعل → نیم‌فاصله (نه فاصله)
   - «ها» / «ای» / «تر» / «ترین» → نیم‌فاصله

6. LaTeX خاص:
   - \lr{...} → <span dir="ltr">...</span>
   - \rl{...} → <span dir="rtl">...</span>
   - \begin{latin} → <div dir="ltr" lang="en">
   - \begin{persian} → <div dir="rtl" lang="fa">
   - \LTRfootnote → پانوشت با dir="ltr"

7. Frontmatter:
   - lang: "fa"
   - dir: "rtl"
   - همیشه حاضر باشند
```

#### ۴.۳.۲ قواعد تبدیل اختصاصی هر فرمت

##### LaTeX → MDX

```markdown
پردازش ترتیبی:
━━━━━━━━━━━━━━

۱. تحلیل preamble:
   - استخراج پکیج‌ها و تنظیمات
   - شناسایی فونت‌ها
   - شناسایی محیط‌های سفارشی (newtheorem, newtcbtheorem, etc.)
   - شناسایی دستورات سفارشی (\newcommand)

۲. بازگشایی ماکروها:
   - \newcommand → بازنویسی inline
   - \input{file} → ادغام فایل
   - \include{file} → ادغام فایل

۳. تبدیل ساختار:
   - \chapter → # (H1)
   - \section → ## (H2)
   - \subsection → ### (H3)
   - \subsubsection → #### (H4)
   - \paragraph → ##### (H5)

۴. تبدیل قالب‌بندی:
   - \textbf{} → **...**
   - \emph{} / \textit{} → *...*
   - \underline{} → <u>...</u>
   - \sout{} → ~~...~~
   - \texttt{} → `...`
   - \textsc{} → <span style="font-variant:small-caps">
   - \footnotesize / \small → <small>

۵. تبدیل محیط‌ها:
   - itemize → - لیست
   - enumerate → 1. لیست
   - description → Definition List
   - figure → <Figure>
   - table → <table> یا pipe table
   - equation/align/gather → $$...$$
   - theorem/definition/proof → کامپوننت‌ها
   - lstlisting/minted → ```code```
   - algorithm2e → شبه‌کد یا کد
   - tikzpicture → SVG/PNG
   - tcolorbox → <Admonition> یا <Box>

۶. تبدیل ارجاعات:
   - \label{} → id
   - \ref{} / \cref{} → لینک
   - \cite{} → ارجاع
   - \footnote{} → پانوشت
   - \bibliography{} → کتاب‌نامه

۷. حذف دستورات غیرضروری:
   - \usepackage{} → حذف
   - \pagestyle{} → حذف
   - \geometry{} → حذف
   - \fancyhf{} → حذف
   - تنظیمات صفحه‌بندی → حذف
```

##### HTML → MDX

```markdown
پردازش ترتیبی:
━━━━━━━━━━━━━━

۱. تحلیل <head>:
   - استخراج <title>, <meta> → frontmatter
   - شناسایی CSS → تبدیل به className
   - شناسایی <script> → حذف یا تبدیل

۲. تمیزکاری HTML:
   - حذف تگ‌های غیرضروری (<div> تودرتو بدون معنا)
   - تبدیل <br> → newline
   - تبدیل &nbsp; → فاصله
   - تبدیل HTML entities → Unicode
   - حذف inline styles → className

۳. تبدیل ساختاری:
   - <h1>-<h6> → #-######
   - <p> → پاراگراف
   - <strong>/<b> → **...**
   - <em>/<i> → *...*
   - <a href> → [text](url)
   - <img> → <Image>
   - <ul>/<ol> → لیست MD
   - <table> → pipe table یا <table> MDX
   - <blockquote> → > نقل‌قول
   - <pre><code> → ```code```
   - <figure> → <Figure>
   - <details> → <Details> کامپوننت
   - <sup>/<sub> → <sup>/<sub>
   - <mark> → <mark>
   - <kbd> → <kbd>
   - <abbr> → <abbr>
   - <time> → <time>
   - <address> → <address>

۴. تبدیل فرم‌ها:
   - <form>, <input>, <select> → <Form> کامپوننت (یا حذف)

۵. تبدیل رسانه:
   - <video>/<iframe> → <Video>/<Embed>
   - <audio> → <Audio>
   - <svg> → فایل مجزا + <Image>

۶. حفظ dir/lang:
   - <div dir="ltr"> → حفظ
   - <span lang="en"> → حفظ
```

##### Markdown → MDX

```markdown

پردازش ترتیبی:
━━━━━━━━━━━━━━

۱. تحلیل Frontmatter:
   - YAML (---) → حفظ و تکمیل
   - TOML (+++) → تبدیل به YAML
   - اعتبارسنجی و تکمیل فیلدهای ناقص

۲. تبدیل عناصر:
   - اکثر عناصر MD مستقیماً در MDX معتبرند → حفظ
   - GFM extensions → بررسی پشتیبانی در MDX pipeline

۳. تبدیل‌های خاص MDX:
   - ```mermaid → <MermaidDiagram chart={`...`} />
   - ![alt](src) → <Image src={src} alt={alt} />  (اختیاری)
   - > [!NOTE] → <Admonition type="note">
   - > [!WARNING] → <Admonition type="warning">
   - > [!TIP] → <Admonition type="tip">
   - > [!CAUTION] → <Admonition type="caution">
   - > [!IMPORTANT] → <Admonition type="important">
   - <details> → <Details> یا <Collapsible>

۴. اضافه کردن import ها:
   - بررسی کامپوننت‌های استفاده‌شده
   - اضافه کردن import خودکار در بالای فایل:
     import Theorem from '@/components/Theorem';
     import MermaidDiagram from '@/components/MermaidDiagram';
     ...

۵. بررسی سازگاری JSX:
   - class → className
   - for → htmlFor
   - style="..." → style={{...}}
   - <!-- comment --> → {/* comment */}
   - خود-بسته‌شونده: <br> → <br />
   - <img> → <img /> یا <Image />

۶. حفظ HTML درون MD:
   - HTML معتبر → حفظ (MDX از HTML پشتیبانی می‌کند)
   - تبدیل به JSX syntax در صورت نیاز
```

##### DOCX → MDX

```markdown
پردازش ترتیبی:
━━━━━━━━━━━━━━

۱. استخراج محتوا:
   - استفاده از python-docx یا pandoc
   - استخراج Core Properties → frontmatter
   - حفظ ساختار Heading Levels

۲. تبدیل سبک‌ها:
   - Heading 1-6 → # تا ######
   - Normal → پاراگراف
   - List Bullet → - لیست
   - List Number → 1. لیست
   - Quote → > نقل‌قول
   - Code → ```code```
   - Table → pipe table یا <table>

۳. تبدیل قالب‌بندی:
   - Bold → **...**
   - Italic → *...*
   - Underline → <u>...</u>
   - Strikethrough → ~~...~~
   - Superscript → <sup>...</sup>
   - Subscript → <sub>...</sub>
   - Highlight → <mark>...</mark>

۴. استخراج تصاویر:
   - تصاویر embed شده → استخراج به پوشه assets
   - تبدیل WMF/EMF → PNG/SVG
   - حفظ alt text

۵. تبدیل فرمول‌ها:
   - OMML (Office Math) → LaTeX → $...$
   - MathType OLE → LaTeX (در صورت امکان)

۶. تبدیل جداول:
   - Simple table → pipe table
   - Merged cells → <table> HTML
   - Table style → CSS classes

۷. حفظ RTL:
   - بررسی paragraph direction
   - بررسی run-level bidi
   - تنظیم dir attributes

۸. پانوشت‌ها:
   - Footnotes → [^fn-N]
   - Endnotes → بخش پی‌نوشت
```

##### PDF → MDX

```markdown
پردازش ترتیبی:
━━━━━━━━━━━━━━

⚠ PDF پیچیده‌ترین فرمت برای تبدیل است.
   کیفیت خروجی بستگی به نوع PDF دارد.

۱. تشخیص نوع PDF:
   - PDF متنی (text-based): بهترین کیفیت
   - PDF اسکن‌شده (image-based): نیاز به OCR
   - PDF ترکیبی: بخشی متن، بخشی تصویر
   - PDF از LaTeX: بهترین حالت (ساختار حفظ شده)

۲. استخراج متن:
   - ابزار اصلی: PyMuPDF (fitz) یا pdfplumber
   - ابزار جایگزین: pdftotext (poppler)
   - OCR: Tesseract + pytesseract (برای تصاویر)
     → با زبان فارسی: tesseract --oem 3 -l fas+eng

۳. بازسازی ساختار:
   - تشخیص عناوین (بر اساس اندازه فونت و بولد بودن)
   - تشخیص پاراگراف‌ها
   - تشخیص لیست‌ها
   - تشخیص جداول (با camelot یا tabula)
   - تشخیص فرمول‌ها (با Nougat یا Mathpix)
   - تشخیص تصاویر (استخراج embedded images)

۴. بازسازی فرمول‌ها:
   - ابزار ۱: Nougat (Meta) — مدل تخصصی PDF→LaTeX
   - ابزار ۲: Mathpix API — تبدیل تصویر فرمول → LaTeX
   - ابزار ۳: InftyReader
   - ابزار ۴: AI (GPT-4 Vision) — برای موارد پیچیده

۵. استخراج تصاویر:
   - PyMuPDF: page.get_images()
   - ذخیره با کیفیت اصلی
   - تعیین محل در متن

۶. پردازش RTL:
   - تشخیص جهت پاراگراف
   - اصلاح ترتیب کاراکترها (logical order vs visual order)
   - بازسازی نیم‌فاصله‌ها (ممکن است از دست رفته باشند)

۷. بررسی کیفیت:
   - مقایسه تعداد صفحات
   - مقایسه تعداد تصاویر
   - مقایسه تقریبی تعداد کلمات
   - امتیاز اطمینان (confidence score)

⚠ محدودیت‌ها:
   - فرمول‌های پیچیده ممکن است نادرست تبدیل شوند
   - جداول پیچیده ممکن است شکسته شوند
   - نیم‌فاصله‌ها ممکن است از دست رفته باشند
   - توصیه: PDF از LaTeX ← بهتر است فایل .tex اصلی تبدیل شود
```

##### RST → MDX

```markdown
پردازش ترتیبی:
━━━━━━━━━━━━━━

۱. تحلیل ساختار:
   - عنوان‌ها (overline/underline) → #-######
   - .. contents:: → TOC
   - .. meta:: → frontmatter

۲. تبدیل Directives:
   - .. note:: → <Admonition type="note">
   - .. warning:: → <Admonition type="warning">
   - .. tip:: → <Admonition type="tip">
   - .. danger:: → <Admonition type="danger">
   - .. admonition:: Title → <Admonition title="Title">
   - .. code-block:: lang → ```lang
   - .. math:: → $$...$$
   - .. figure:: → <Figure>
   - .. image:: → <Image>
   - .. table:: → <table>
   - .. csv-table:: → pipe table
   - .. list-table:: → pipe table
   - .. topic:: → <Box>
   - .. sidebar:: → <Sidebar>
   - .. epigraph:: → <Blockquote>
   - .. pull-quote:: → <Blockquote>
   - .. container:: class → <div className="class">
   - .. raw:: html → حفظ HTML

۳. تبدیل Roles:
   - :math:`...` → $...$
   - :ref:`label` → [text](#label)
   - :doc:`path` → [text](path)
   - :download:`path` → [text](path)
   - :abbr:`text (explanation)` → <abbr title="explanation">text</abbr>
   - :kbd:`key` → <kbd>key</kbd>

۴. تبدیل پانوشت/ارجاع:
   - [#fn]_ → [^fn]
   - [label]_ → [text](#label) یا [text](url)
   - .. [label] → تعریف ارجاع

۵. Field Lists:
   - :field: value → متادیتا یا definition list
```

##### AsciiDoc → MDX

```markdown
پردازش ترتیبی:
━━━━━━━━━━━━━━

۱. تحلیل Header:
   - = Title → # (H1)
   - :attribute: → frontmatter
   - Author line → author metadata

۲. تبدیل ساختار:
   - == Section → ## (H2)
   - === Subsection → ### (H3)
   - .Title → عنوان بلوک
   - [options] → تنظیمات بلوک

۳. تبدیل بلوک‌ها:
   - [source,lang]---- → ```lang
   - [stem]++++ → $$...$$
   - [NOTE]==== → <Admonition type="note">
   - [WARNING]==== → <Admonition type="warning">
   - [TIP]==== → <Admonition type="tip">
   - [IMPORTANT]==== → <Admonition type="important">
   - [CAUTION]==== → <Admonition type="caution">
   - [quote,author]____ → <Blockquote>
   - [%collapsible]==== → <Details>
   - |=== table → pipe table یا <table>
   - image::path[] → <Image>

۴. تبدیل Inline:
   - *bold* → **bold**
   - _italic_ → *italic*
   - `mono` → `mono`
   - stem:[...] → $...$
   - <<anchor>> → [text](#anchor)
   - footnote:[text] → [^fn]
   - btn:[text] → <Button>
   - kbd:[key] → <kbd>key</kbd>
   - menu:path[] → breadcrumb
```

##### EPUB → MDX

```markdown
پردازش ترتیبی:
━━━━━━━━━━━━━━

۱. استخراج:
   - EPUB = ZIP حاوی XHTML + CSS + تصاویر + metadata
   - استخراج content.opf → متادیتا
   - استخراج toc.ncx یا nav.xhtml → فهرست مطالب

۲. تبدیل فصل‌ها:
   - هر فایل XHTML → یک فایل MDX
   - یا ادغام همه → یک فایل MDX

۳. تبدیل XHTML → MDX:
   - مشابه HTML → MDX

۴. مدیریت تصاویر:
   - استخراج از EPUB archive
   - کپی به پوشه assets
```

##### Jupyter Notebook → MDX

```markdown
پردازش ترتیبی:
━━━━━━━━━━━━━━

۱. تحلیل .ipynb (JSON):
   - metadata → frontmatter
   - cells → بخش‌های محتوا

۲. تبدیل سلول‌ها:
   - markdown cell → محتوای MDX مستقیم
   - code cell → ```python ... ```
   - code output (text) → بلوک خروجی
   - code output (image) → <Image>
   - code output (HTML) → تبدیل HTML

۳. مدیریت خروجی‌ها:
   - stdout → <Output type="stdout">
   - stderr → <Output type="stderr">
   - display_data (image/png) → استخراج + <Image>
   - display_data (text/html) → تبدیل HTML
   - execute_result → <Output>
```

#### ۴.۳.۳ ساختار خروجی MDX

```
خروجی نمونه برای یک مقاله:
━━━━━━━━━━━━━━━━━━━━━━━━━━

de-morgans-laws/
├── index.mdx                  ← فایل اصلی MDX
└── assets/
    ├── diagram1.svg           ← نمودار تبدیل‌شده از TikZ
    ├── proof-tree.svg         ← درخت اثبات
    └── cover.webp             ← تصویر شاخص (بهینه‌شده)


خروجی نمونه برای یک کتاب:
━━━━━━━━━━━━━━━━━━━━━━━━━

logic-foundations/
├── _series.json               ← متادیتای مجموعه
├── 00-introduction/
│   ├── index.mdx
│   └── assets/
├── 01-propositional-logic/
│   ├── index.mdx
│   └── assets/
│       ├── truth-table.svg
│       └── demorgan-proof.svg
├── 02-predicate-logic/
│   ├── index.mdx
│   └── assets/
├── bibliography.json          ← کتاب‌نامه مشترک
└── shared-assets/
    └── cover.webp
```

```mdx
{/* === نمونه خروجی MDX === */}

---
title: "قانون دمورگان و کاربردهای آن"
titleEn: "De Morgan's Laws and Their Applications"
slug: "de-morgans-laws"
date: "2025-07-13"
author:
  name: "مهدی سالم"
  nameEn: "Mahdi Salem"
  email: "mahhdy@gmail.com"
lang: "fa"
dir: "rtl"
type: "article"
tags: ["منطق", "دمورگان", "اثبات", "گزاره‌ای"]
tagsEn: ["logic", "de-morgan", "proof", "propositional"]
categories: ["منطق ریاضی"]
description: "بررسی و اثبات قوانین دمورگان در منطق گزاره‌ای با جدول ارزش و روش استنتاج طبیعی"
math: true
mermaid: true
codeHighlight: true
toc: true
sourceFormat: "latex"
sourceFile: "demorgan.tex"
convertedAt: "2025-07-13T15:30:42+03:30"
converterVersion: "FormatForge 1.0.0"
qualityScore: 95
---

import Theorem from '@/components/Theorem';
import Definition from '@/components/Definition';
import Proof from '@/components/Proof';
import Example from '@/components/Example';
import Admonition from '@/components/Admonition';
import Figure from '@/components/Figure';
import MermaidDiagram from '@/components/MermaidDiagram';
import CrossRef from '@/components/CrossRef';
import Citation from '@/components/Citation';

# قانون دمورگان و کاربردهای آن

{/* ... محتوای تبدیل‌شده ... */}
```

#### ۴.۳.۴ نمایش پیشرفت و خطاها

```powershell
🔄 تبدیل: logic-book/ → MDX
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📄 فایل ۱/۴: main.tex
  [████████████████████████████████████████] 100%
  ✅ Frontmatter استخراج شد
  ✅ ۳ فصل شناسایی شد
  ⏭ پردازش فصل‌ها به‌صورت مجزا

📄 فایل ۲/۴: chapter01.tex
  [████████████████████░░░░░░░░░░░░░░░░░░░] 52%
  ✅ عناوین: ۴ بخش تبدیل شد
  ✅ ریاضی: ۱۲ فرمول تبدیل شد
  ⚠ TikZ: نمودار خط ۸۵ → تبدیل به SVG...
  [████████████████████████████████░░░░░░░] 78%
  ✅ TikZ → SVG: assets/ch01-fig-01.svg (12 KB)
  ✅ جداول: ۲ جدول تبدیل شد
  ✅ قضیه‌ها: ۳ قضیه + ۲ تعریف + ۳ اثبات
  ✅ پانوشت: ۴ پانوشت
  ✅ ارجاعات: ۶ ارجاع متقاطع
  [████████████████████████████████████████] 100%
  ✅ chapter01.tex → 01-introduction/index.mdx

📄 فایل ۳/۴: chapter02.tex
  [████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░] 30%
  ⚠ هشدار: فرمول خط ۱۵۷ → \begin{align} بدون \end{align}
    → اصلاح خودکار: اضافه شد \end{aligned} (تأیید؟ [Y/n])
  [████████████████████████████████████████] 100%
  ✅ chapter02.tex → 02-propositional-logic/index.mdx

📄 فایل ۴/۴: references.bib
  ✅ ۱۵ مرجع → bibliography.json

📊 آمار نهایی:
━━━━━━━━━━━━━━
  فایل‌های MDX تولیدشده: ۳
  تصاویر/SVG: ۵ فایل (۱۸۰ KB)
  فرمول‌ها: ۴۲ (همه موفق ✅)
  جداول: ۷ (همه موفق ✅)
  نمودارها: ۳ TikZ→SVG (همه موفق ✅)
  کد: ۴ بلوک (همه موفق ✅)
  ارجاعات: ۱۸ (۱۶ موفق ✅, ۲ هشدار ⚠)
  نیم‌فاصله: ۲۳۴ (قبل) → ۲۳۴ (بعد) ✅ بدون تغییر
  زمان: ۳۸ ثانیه

  ⚠ هشدارها:
    1. ۲ ارجاع به فصل ۳ که هنوز تبدیل نشده
       → پیشنهاد: بعد از تبدیل فصل ۳ لینک‌ها اصلاح شوند
    2. فرمول خط ۱۵۷ اصلاح خودکار شد

  ادامه به مرحله تست؟ [Y/n]: █
```

---

### ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
### STAGE 4: تست کیفیت خروجی
### ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

#### ۴.۴.۱ سطوح تست

```markdown
سطح ۱: تست ساختاری (Structural Test)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

☐ Frontmatter YAML معتبر است
☐ تمام فیلدهای اجباری حاضرند
☐ تمام import ها وجود دارند و صحیح‌اند
☐ JSX syntax معتبر است (parse بدون خطا)
☐ تمام تگ‌ها بسته شده‌اند
☐ تمام کامپوننت‌ها import شده‌اند
☐ فایل بدون خطای MDX compile می‌شود
☐ encoding خروجی UTF-8 است

سطح ۲: تست محتوایی (Content Test)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

☐ تعداد عناوین ورودی = تعداد عناوین خروجی
☐ تعداد پاراگراف‌ها تقریباً برابر
☐ تعداد فرمول‌ها: ورودی = خروجی
☐ تعداد تصاویر: ورودی = خروجی
☐ تعداد جداول: ورودی = خروجی
☐ تعداد بلوک‌های کد: ورودی = خروجی
☐ تعداد لینک‌ها: ورودی ≈ خروجی
☐ تعداد پانوشت‌ها: ورودی = خروجی
☐ تعداد ارجاعات کتاب‌نامه: ورودی = خروجی
☐ تعداد ZWNJ: ورودی = خروجی
☐ تعداد کلمات: اختلاف < ۵٪

سطح ۳: تست ریاضی (Math Test)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

☐ تمام فرمول‌های inline با KaTeX parse می‌شوند
☐ تمام فرمول‌های display با KaTeX parse می‌شوند
☐ \begin{aligned} / \end{aligned} جفت هستند
☐ \begin{cases} / \end{cases} جفت هستند
☐ \begin{pmatrix} / \end{pmatrix} جفت هستند
☐ تمام ماکروهای LaTeX شناخته‌شده هستند
☐ \label → id تبدیل شده
☐ \ref → لینک تبدیل شده

سطح ۴: تست فارسی/RTL (Persian Test)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

☐ dir="rtl" در frontmatter هست
☐ lang="fa" در frontmatter هست
☐ نیم‌فاصله‌ها حفظ شده‌اند (شمارش ZWNJ)
☐ گیومه‌ها «» هستند (نه "")
☐ بلوک‌های کد dir="ltr" دارند
☐ بلوک‌های انگلیسی dir="ltr" دارند
☐ \lr{} → <span dir="ltr"> تبدیل شده
☐ \begin{latin} → <div dir="ltr"> تبدیل شده
☐ متن فارسی درون فرمول حفظ شده (\text{اگر})

سطح ۵: تست لینک‌ها (Link Test)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

☐ تمام لینک‌های داخلی (anchor) هدف دارند
☐ تمام فایل‌های تصویر ارجاع‌شده وجود دارند
☐ تمام لینک‌های بین فصل‌ها صحیح‌اند
☐ لینک‌های خارجی فرمت صحیح دارند (اختیاری: HTTP check)

سطح ۶: تست بصری (Visual Test) — اختیاری
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

☐ رندر MDX در headless browser (Playwright/Puppeteer)
☐ اسکرین‌شات خودکار
☐ مقایسه بصری با PDF اصلی (اختیاری)
☐ بررسی رندر فرمول‌ها
☐ بررسی رندر نمودارها
☐ بررسی جهت RTL
```

#### ۴.۴.۲ امتیاز کیفیت (Quality Score)

```python
# محاسبه امتیاز کیفیت 0-100

quality_score = 0

# ساختار (25 امتیاز)
structural_tests = [frontmatter_valid, jsx_valid, imports_valid,
                    encoding_valid, compiles_ok]
quality_score += (sum(structural_tests) / len(structural_tests)) * 25

# محتوا (25 امتیاز)
content_ratio = min(
    headings_ratio,    # تعداد عناوین ورودی/خروجی
    formulas_ratio,    # تعداد فرمول‌ها ورودی/خروجی
    images_ratio,      # تعداد تصاویر ورودی/خروجی
    tables_ratio,      # تعداد جداول ورودی/خروجی
    code_ratio,        # تعداد کد ورودی/خروجی
    words_ratio,       # تعداد کلمات (تقریبی)
)
quality_score += content_ratio * 25

# ریاضی (20 امتیاز)
math_parse_rate = formulas_parseable / total_formulas
quality_score += math_parse_rate * 20

# فارسی (20 امتیاز)
persian_tests = [rtl_set, lang_set, zwnj_preserved,
                 quotes_correct, bidi_correct]
quality_score += (sum(persian_tests) / len(persian_tests)) * 20

# لینک‌ها (10 امتیاز)
link_validity = valid_links / total_links
quality_score += link_validity * 10

# درجه‌بندی:
# 90-100: عالی ✅ — آماده انتشار
# 75-89:  خوب 🟡 — بررسی دستی جزئی
# 50-74:  متوسط 🟠 — نیاز به اصلاح
# 0-49:   ضعیف 🔴 — تبدیل مجدد
```

#### ۴.۴.۳ گزارش تست

```markdown
🧪 گزارش تست کیفیت:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 امتیاز کلی: ۹۵/۱۰۰ ✅ عالی

سطح ۱ — ساختاری:
  ✅ Frontmatter YAML معتبر
  ✅ JSX syntax معتبر
  ✅ تمام import ها صحیح
  ✅ Encoding: UTF-8
  ✅ MDX compile: موفق

سطح ۲ — محتوایی:
  ✅ عناوین: ۱۲/۱۲ (۱۰۰٪)
  ✅ فرمول‌ها: ۴۲/۴۲ (۱۰۰٪)
  ✅ تصاویر: ۵/۵ (۱۰۰٪)
  ✅ جداول: ۷/۷ (۱۰۰٪)
  ✅ کد: ۴/۴ (۱۰۰٪)
  ✅ پانوشت: ۸/۸ (۱۰۰٪)
  ⚠️ ارجاعات: ۱۶/۱۸ (۸۹٪)
     → ۲ ارجاع به فصل تبدیل‌نشده
  ✅ کلمات: ۳,۲۴۵ ≈ ۳,۲۵۱ (اختلاف ۰.۲٪)

سطح ۳ — ریاضی:
  ✅ KaTeX parse: ۴۲/۴۲ (۱۰۰٪)
  ✅ محیط‌های تودرتو: صحیح
  ✅ ارجاعات label/ref: ۱۲/۱۲

سطح ۴ — فارسی/RTL:
  ✅ dir="rtl" ✓
  ✅ lang="fa" ✓
  ✅ ZWNJ: ۲۳۴/۲۳۴ (۱۰۰٪ حفظ شده)
  ✅ گیومه «»: ۱۸/۱۸
  ✅ بلوک‌های LTR: ۶/۶ صحیح
  ✅ \lr{} تبدیل: ۱۴/۱۴

سطح ۵ — لینک‌ها:
  ✅ لینک‌های داخلی: ۱۴/۱۴
  ⚠️ لینک‌های بین‌فصلی: ۲ معلق
  ✅ تصاویر: ۵/۵ موجود
  ✅ لینک‌های خارجی: ۴/۴ فرمت صحیح

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  [D] ادامه به استقرار (Deploy)
  [V] تست بصری (نیاز به headless browser)
  [R] بازگشت و اصلاح ۲ ارجاع معلق
  [E] باز کردن فایل MDX در ویرایشگر
  [Q] لغو

  انتخاب شما: █
```

---

### ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
### STAGE 5: استقرار خروجی
### ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

#### ۴.۵.۱ تنظیمات وب‌سایت

```yaml
# config/website_config.yaml

website:
  name: "بلاگ ریاضی من"
  framework: "next"          # next | astro | gatsby | docusaurus | custom
  content_dir: "content/"    # مسیر نسبی محتوا
  assets_dir: "public/assets/"  # مسیر نسبی asset ها
  base_url: "https://mysite.com"

  paths:
    articles: "content/articles/"
    books: "content/books/"
    proofs: "content/proofs/"
    images: "public/assets/images/"
    files: "public/assets/files/"

  naming:
    # الگوی نام‌گذاری پوشه‌ها
    article_dir: "{slug}/"
    book_dir: "{series_slug}/{chapter_slug}/"
    # الگوی نام فایل اصلی
    main_file: "index.mdx"
    # الگوی نام تصاویر
    image_file: "{slug}-{type}-{number}.{ext}"

  components:
    # مسیر کامپوننت‌های MDX
    theorem: "@/components/mdx/Theorem"
    definition: "@/components/mdx/Definition"
    proof: "@/components/mdx/Proof"
    example: "@/components/mdx/Example"
    admonition: "@/components/mdx/Admonition"
    figure: "@/components/mdx/Figure"
    mermaid: "@/components/mdx/MermaidDiagram"
    citation: "@/components/mdx/Citation"
    cross_ref: "@/components/mdx/CrossRef"

  optimization:
    convert_images_to_webp: true
    max_image_width: 1200
    svgo_optimize: true
    minify_html_in_mdx: false

  git:
    auto_commit: false       # commit خودکار بعد از استقرار
    commit_message: "feat(content): add {title}"
    branch: "content/{slug}"
```

#### ۴.۵.۲ فرآیند استقرار

```markdown
🚀 استقرار خروجی:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📁 مقصد: C:\Projects\my-blog\content\books\logic-foundations\

مراحل:
  ✅ ۱. ساخت ساختار پوشه‌ها
       └── logic-foundations/
           ├── 00-introduction/
           ├── 01-propositional-logic/
           └── 02-predicate-logic/

  ✅ ۲. کپی فایل‌های MDX
       ├── 00-introduction/index.mdx (8.2 KB)
       ├── 01-propositional-logic/index.mdx (12.5 KB)
       └── 02-predicate-logic/index.mdx (10.1 KB)

  ✅ ۳. کپی و بهینه‌سازی تصاویر
       ├── 00-introduction/assets/
       │   └── cover.webp (45 KB ← 180 KB PNG, ۷۵٪ کاهش)
       ├── 01-propositional-logic/assets/
       │   ├── truth-table.svg (3 KB ← 5 KB, SVGO)
       │   └── demorgan-proof.svg (8 KB)
       └── shared-assets/
           └── series-cover.webp (62 KB)

  ✅ ۴. تولید فایل‌های جانبی
       ├── _series.json (متادیتای مجموعه)
       └── bibliography.json (۱۵ مرجع)

  ✅ ۵. بروزرسانی لینک‌های نسبی
       → ۱۸ لینک بین‌فصلی اصلاح شد

  ✅ ۶. اعتبارسنجی نهایی
       → تمام فایل‌ها خوانا و سالم هستند
       → تمام تصاویر ارجاع‌شده وجود دارند
       → تمام لینک‌های داخلی معتبرند

📊 خلاصه:
  فایل‌های MDX: ۳
  تصاویر: ۴ (۱۱۸ KB مجموع)
  فایل‌های JSON: ۲
  حجم کل: ۱۴۹ KB

  [O] باز کردن پوشه در Explorer
  [G] Git commit (branch: content/logic-foundations)
  [P] پیش‌نمایش در مرورگر (next dev)
  [C] ادامه به گزارش
  [Q] پایان

  انتخاب شما: █
```

---

### ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
### STAGE 6: گزارش مرکزی
### ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

#### ۴.۶.۱ ساختار گزارش مرکزی

```yaml
# reports/central_log.yaml
# این فایل تاریخچه کامل تمام تبدیل‌ها را نگه می‌دارد

version: "1.0"
last_updated: "2025-07-13T16:45:00+03:30"
total_conversions: 42
total_documents: 128
total_failures: 3

conversions:
  - id: "conv_20250713_153042"
    timestamp: "2025-07-13T15:30:42+03:30"
    status: "success"           # success | partial | failed
    
    input:
      path: "D:\Code\Apps\formatforge\docs"
      type: "directory"
      structure: "multi_chapter_book"
      format: "latex"
      files_count: 7
      total_size_bytes: 245000
    
    output:
      path: "C:/Projects/my-blog/content/books/logic-foundations/"
      mdx_files: 3
      asset_files: 6
      total_size_bytes: 152000
      quality_score: 95
    
    metadata:
      title: "مبانی منطق ریاضی و اثبات‌های صوری"
      slug: "logic-foundations"
      lang: "fa"
      type: "book"
      chapters: 3
    
    stats:
      duration_seconds: 38
      formulas_converted: 42
      images_converted: 5
      tables_converted: 7
      code_blocks: 4
      footnotes: 8
      cross_refs: 18
      zwnj_preserved: "234/234"
    
    warnings:
      - "۲ ارجاع به فصل تبدیل‌نشده"
      - "فرمول خط ۱۵۷ اصلاح خودکار شد"
    
    errors: []

  - id: "conv_20250712_091500"
    timestamp: "2025-07-12T09:15:00+03:30"
    status: "partial"
    # ...

# آمار تجمعی
statistics:
  by_format:
    latex: { count: 25, success: 24, avg_quality: 92 }
    markdown: { count: 10, success: 10, avg_quality: 97 }
    html: { count: 4, success: 4, avg_quality: 88 }
    docx: { count: 2, success: 1, avg_quality: 75 }
    pdf: { count: 1, success: 0, avg_quality: 0 }
  
  by_language:
    fa: 18
    en: 12
    fa_en: 12
  
  by_type:
    article: 30
    book: 3
    chapter: 9
    proof: 0
  
  slugs_used:       # برای جلوگیری از تکرار
    - "de-morgans-laws"
    - "logic-foundations"
    - "logic-foundations/ch01-introduction"
    # ...
```

#### ۴.۶.۲ نمایش گزارش

```
📊 گزارش مرکزی FormatForge:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📈 آمار کلی:
  تبدیل‌ها: ۴۲ (موفق: ۳۹ | ناقص: ۲ | ناموفق: ۱)
  اسناد: ۱۲۸ فایل MDX تولیدشده
  میانگین کیفیت: ۹۱/۱۰۰

📋 آخرین ۵ تبدیل:
  ─────────────────────────────────────────────
  # │ تاریخ       │ عنوان                     │ فرمت │ کیفیت │ وضعیت
  ─────────────────────────────────────────────
  1 │ ۱۴۰۴/۰۴/۲۲ │ مبانی منطق ریاضی          │ LaTeX│  ۹۵  │  ✅
  2 │ ۱۴۰۴/۰۴/۲۱ │ نمونه مارک‌داون            │  MD  │  ۹۸  │  ✅
  3 │ ۱۴۰۴/۰۴/۲۱ │ صفحه HTML تست             │ HTML │  ۸۸  │  ✅
  4 │ ۱۴۰۴/۰۴/۲۰ │ مقاله منطق موجهات          │ DOCX │  ۷۵  │  ⚠️
  5 │ ۱۴۰۴/۰۴/۱۹ │ جزوه آنالیز               │  PDF │  ۴۲  │  ❌

📊 نمودار فرمت‌ها:
  LaTeX    ████████████████████████░ ۶۰٪ (25)
  Markdown ██████████░░░░░░░░░░░░░░ ۲۴٪ (10)
  HTML     ████░░░░░░░░░░░░░░░░░░░░ ۱۰٪ (4)
  DOCX     ██░░░░░░░░░░░░░░░░░░░░░░  ۵٪ (2)
  PDF      █░░░░░░░░░░░░░░░░░░░░░░░  ۲٪ (1)

  [D] جزئیات یک تبدیل
  [E] خروجی CSV/JSON
  [S] جستجو
  [Q] بازگشت

  انتخاب شما: █
```

---

## ۵. وابستگی‌ها و ابزارهای خارجی

### ۵.۱ وابستگی‌های Python

```
# requirements.txt

# === هسته ===
click>=8.1                    # CLI framework
rich>=13.7                    # ترمینال زیبا
textual>=0.70                 # TUI framework (اختیاری)
pyyaml>=6.0                   # YAML parsing
toml>=0.10                    # TOML parsing
pydantic>=2.5                 # اعتبارسنجی داده

# === تشخیص فایل ===
python-magic>=0.4             # تشخیص نوع فایل
chardet>=5.2                  # تشخیص encoding

# === تبدیل‌گرها ===
pypandoc>=1.13                # رابط Python برای Pandoc
beautifulsoup4>=4.12          # تحلیل HTML
lxml>=5.1                     # تحلیل XML/HTML
python-docx>=1.1              # خواندن DOCX
pymupdf>=1.23                 # خواندن PDF (fitz)
pdfplumber>=0.11              # استخراج جدول از PDF
ebooklib>=0.18                # خواندن EPUB
nbformat>=5.10                # خواندن Jupyter Notebooks

# === ریاضی ===
flatlatex>=0.15               # ساده‌سازی LaTeX
# یا
pylatexenc>=2.10              # تبدیل LaTeX ← Unicode

# === تصویر ===
pillow>=10.2                  # پردازش تصویر
cairosvg>=2.7                 # SVG → PNG
svgutils>=0.3                 # ویرایش SVG

# === AI (اختیاری) ===
openai>=1.35                  # OpenAI API
anthropic>=0.30               # Anthropic API
google-generativeai>=0.5      # Google Gemini

# === تست ===
playwright>=1.44              # تست بصری با headless browser

# === گزارش ===
jinja2>=3.1                   # قالب‌سازی گزارش
tabulate>=0.9                 # جداول متنی
```

### ۵.۲ ابزارهای خارجی

```
ابزار              │ استفاده                   │ نصب
━━━━━━━━━━━━━━━━━━━┿━━━━━━━━━━━━━━━━━━━━━━━━━━━┿━━━━━━━━━━━━━━━━━━━━━
Pandoc             │ تبدیل‌گر عمومی            │ winget install Pandoc
XeLaTeX            │ کامپایل LaTeX + TikZ→SVG  │ TeX Live / MiKTeX
Biber              │ کتاب‌نامه LaTeX            │ همراه TeX Live
dvisvgm            │ تبدیل TikZ → SVG          │ همراه TeX Live
ImageMagick        │ تبدیل/بهینه‌سازی تصویر    │ winget install ImageMagick
SVGO               │ بهینه‌سازی SVG             │ npm install -g svgo
cwebp              │ تبدیل به WebP             │ همراه libwebp
Tesseract OCR      │ OCR برای PDF اسکن‌شده     │ winget install Tesseract
Node.js            │ اجرای Mermaid CLI         │ winget install Node.js
mermaid-cli        │ رندر Mermaid → SVG/PNG    │ npm install -g @mermaid-js/mermaid-cli
Playwright         │ تست بصری                  │ pip install playwright
```

---

## ۶. تنظیمات و سفارشی‌سازی

### ۶.۱ فایل تنظیمات کاربر

```yaml
# config/user_config.yaml

# === عمومی ===
general:
  language: "fa"                    # زبان رابط: fa | en
  verbose: true                     # نمایش جزئیات بیشتر
  color: true                       # خروجی رنگی
  confirm_before_convert: true      # تأیید قبل از تبدیل
  confirm_before_deploy: true       # تأیید قبل از استقرار
  auto_fix_warnings: false          # اصلاح خودکار هشدارها
  temp_dir: "~/.formatforge/temp/"
  log_dir: "~/.formatforge/logs/"
  report_file: "~/.formatforge/central_log.yaml"

# === اسکن ===
scanner:
  max_file_size_mb: 100             # حداکثر اندازه فایل
  supported_formats:
    - latex   # .tex
    - html    # .html, .htm, .xhtml
    - markdown # .md, .mdx, .markdown
    - docx    # .docx
    - pdf     # .pdf
    - rst     # .rst
    - asciidoc # .adoc, .asciidoc
    - epub    # .epub
    - notebook # .ipynb
  ignore_patterns:
    - "*.aux"
    - "*.log"
    - "*.synctex*"
    - "*.fls"
    - "*.fdb_latexmk"
    - ".git/"
    - "node_modules/"
    - "__pycache__/"
    - ".DS_Store"
    - "Thumbs.db"

# === متادیتا ===
metadata:
  default_author:
    name: "مهدی سالم"
    nameEn: "Mahdi Salem"
    email: "mahhdy@gmail.com"
  default_lang: "fa"
  default_dir: "rtl"
  slug_max_length: 60
  slug_transliterate: true          # transliterate فارسی → لاتین
  ai_provider: "openai"            # openai | anthropic | google | ollama | none
  ai_model: "gpt-4o"
  ai_auto_complete:
    description: true
    tags: true
    title_en: true
    slug: true
  require_fields:
    - title
    - slug
    - date
    - lang
    - dir
    - author

# === تبدیل ===
conversion:
  # --- ریاضی ---
  math:
    engine: "katex"                 # katex | mathjax
    display_mode_delimiters: ["$$", "$$"]
    inline_mode_delimiters: ["$", "$"]
    throw_on_error: false
    macros: {}                      # ماکروهای سفارشی KaTeX

  # --- نمودار ---
  diagrams:
    tikz_to: "svg"                  # svg | png
    tikz_dpi: 300                   # DPI برای PNG
    mermaid_to: "component"         # component | svg | png
    mermaid_theme: "base"

  # --- تصویر ---
  images:
    optimize: true
    convert_to_webp: true
    max_width: 1200
    quality: 85
    svg_optimize: true

  # --- کد ---
  code:
    add_line_numbers: false
    default_language: "text"
    highlight_theme: "github-dark"

  # --- جدول ---
  tables:
    complex_to_html: true           # جداول ادغامی → HTML
    simple_to_markdown: true        # جداول ساده → MD pipe

  # --- فارسی ---
  persian:
    preserve_zwnj: true             # حفظ نیم‌فاصله (غیرقابل تغییر!)
    fix_arabic_yeh: true            # تبدیل ي → ی
    fix_arabic_keh: true            # تبدیل ك → ک
    fix_spacing: true               # اصلاح فاصله‌گذاری فارسی
    numerals: "persian"             # persian | latin | keep
    quotation_marks: "guillemet"    # guillemet «» | standard ""

  # --- MDX ---
  mdx:
    component_style: "import"       # import | inline | global
    jsx_runtime: "react"            # react | preact
    mdx_version: 3                  # 2 | 3

# === تست ===
testing:
  run_structural: true
  run_content: true
  run_math: true
  run_persian: true
  run_links: true
  run_visual: false                 # نیاز به Playwright
  min_quality_score: 80             # حداقل امتیاز قبول
  visual_compare_with_source: false # مقایسه بصری با اصل

# === استقرار ===
deployment:
  target_dir: "C:/Projects/my-blog/"
  create_backup: true
  backup_dir: "~/.formatforge/backups/"
  overwrite_existing: "ask"         # ask | yes | no | rename
  post_deploy:
    open_in_editor: false
    editor_command: "code"          # VS Code
    run_dev_server: false
    dev_command: "npm run dev"
    git_commit: false
    git_push: false

# === گزارش ===
reporting:
  format: "yaml"                    # yaml | json | csv | html
  keep_history: true
  max_history: 1000
  export_on_milestone: true         # خروجی گزارش هر ۱۰ تبدیل
```

---

## ۷. دستورات CLI

```bash
# === نصب ===
pip install formatforge
# یا
pip install -e .  # از مخزن

# === راهنما ===
formatforge --help
formatforge <command> --help

# === اسکن ===
formatforge scan ./path/to/input
formatforge scan ./article.tex
formatforge scan ./archive.zip
formatforge scan --recursive ./folder/

# === تبدیل ===
formatforge convert ./input.tex
formatforge convert ./input.tex --output ./output/
formatforge convert ./input.tex --format latex --quality-min 85
formatforge convert ./folder/ --batch --parallel 4

# === تبدیل تعاملی (wizard) ===
formatforge convert --interactive ./input/

# === تست ===
formatforge test ./output/article/index.mdx
formatforge test ./output/ --recursive --visual
formatforge test ./output/ --report-format html

# === استقرار ===
formatforge deploy ./output/ --target C:/Projects/my-blog/
formatforge deploy ./output/ --git-commit --git-push

# === گزارش ===
formatforge report
formatforge report --last 10
formatforge report --export csv --output report.csv
formatforge report --stats
formatforge report --search "منطق"

# === تنظیمات ===
formatforge config init                # ساخت فایل تنظیمات
formatforge config show                # نمایش تنظیمات فعلی
formatforge config set conversion.math.engine katex
formatforge config website             # تنظیم وب‌سایت (wizard)

# === یکجا (all-in-one) ===
formatforge run ./input/ --output ./blog/content/
# معادل: scan → metadata → precheck → convert → test → deploy

# === بررسی سلامت ===
formatforge doctor
# بررسی نصب بودن تمام وابستگی‌ها و ابزارها
```

---

## ۸. مدیریت خطا و بازیابی

```
استراتژی مدیریت خطا:
━━━━━━━━━━━━━━━━━━━━━

۱. خطاهای قابل‌اصلاح خودکار (Auto-fix):
   - Encoding اشتباه → تبدیل به UTF-8 BOM
   - \begin بدون \end → اضافه کردن \end
   - تگ HTML بسته‌نشده → بستن خودکار
   - ي عربی → ی فارسی
   - ك عربی → ک فارسی
   → همه auto-fix ها ثبت و گزارش می‌شوند

۲. خطاهای نیازمند تأیید کاربر:
   - فرمول مبهم (چند تفسیر ممکن)
   - تصویر گمشده (حذف ارجاع؟ placeholder؟)
   - ساختار مبهم (کتاب یا مقالات مستقل؟)
   → نمایش گزینه‌ها و دریافت انتخاب

۳. خطاهای مسدودکننده:
   - فایل خراب / غیرقابل خواندن
   - encoding کاملاً ناشناخته
   - PDF اسکن‌شده بدون OCR
   → پیام خطای واضح + پیشنهاد راه‌حل

۴. بازیابی (Recovery):
   - هر مرحله checkpoint دارد
   - در صورت خطا: بازگشت به آخرین checkpoint
   - فایل‌های موقت تا تأیید نهایی حفظ می‌شوند
   - امکان از سرگیری تبدیل ناتمام:
     formatforge resume --id conv_20250713_153042
```

---

## ۹. ملاحظات عملکرد

```
بهینه‌سازی عملکرد:
━━━━━━━━━━━━━━━━━━

۱. پردازش موازی:
   - تبدیل فصل‌های مستقل به‌صورت parallel
   - بهینه‌سازی تصاویر به‌صورت parallel
   - تعداد thread قابل تنظیم

۲. کَش (Caching):
   - کَش تبدیل TikZ → SVG (بر اساس hash محتوا)
   - کَش بهینه‌سازی تصویر
   - کَش نتایج AI (تکمیل متادیتا)
   - مسیر کَش: ~/.formatforge/cache/

۳. Lazy Loading:
   - وابستگی‌های سنگین (playwright, AI SDKs) فقط در صورت نیاز import شوند

۴. Memory Management:
   - PDF های بزرگ: پردازش صفحه‌به‌صفحه
   - تصاویر بزرگ: streaming
```

---

## ۱۰. تست‌پذیری و CI/CD

```python
# تست‌های واحد با pytest

# test_scanner.py
def test_detect_latex_file():
    """تشخیص صحیح فایل LaTeX"""

def test_detect_zip_with_book():
    """تشخیص کتاب چندفصلی درون ZIP"""

def test_encoding_detection_utf8_bom():
    """تشخیص صحیح UTF-8 BOM"""

# test_converter_latex.py
def test_demorgan_formula():
    """تبدیل صحیح فرمول دمورگان"""

def test_theorem_environment():
    """تبدیل محیط theorem به کامپوننت"""

def test_zwnj_preservation():
    """حفظ نیم‌فاصله در تبدیل"""

def test_lr_command():
    """تبدیل \\lr{} به <span dir='ltr'>"""

def test_tikz_to_svg():
    """تبدیل نمودار TikZ به SVG"""

def test_bibliography_conversion():
    """تبدیل کتاب‌نامه biblatex به JSON"""

def test_cross_references():
    """تبدیل ارجاعات متقاطع \\ref و \\cref"""

def test_footnotes_persian():
    """تبدیل پانوشت فارسی و LTRfootnote"""

def test_nested_environments():
    """تبدیل محیط‌های تودرتو (theorem درون section)"""

def test_custom_commands():
    """بازگشایی \\newcommand های سفارشی"""

def test_multi_chapter_book():
    """تبدیل کتاب چندفصلی با \\input"""

def test_table_with_merged_cells():
    """تبدیل جدول با multirow/multicolumn"""

def test_wrapfigure():
    """تبدیل تصویر کنار متن"""

def test_algorithm2e():
    """تبدیل محیط الگوریتم"""

def test_color_boxes():
    """تبدیل tcolorbox به Admonition"""

# test_converter_html.py
def test_html_meta_extraction():
    """استخراج متادیتا از تگ‌های meta"""

def test_html_dir_preservation():
    """حفظ dir=rtl و dir=ltr"""

def test_html_math_katex():
    """تبدیل فرمول‌های KaTeX/MathJax از HTML"""

def test_html_table_colspan():
    """تبدیل جدول با colspan/rowspan"""

def test_html_form_elements():
    """تبدیل عناصر فرم"""

def test_html_media_elements():
    """تبدیل video/audio/iframe"""

def test_html_svg_inline():
    """تبدیل SVG درون‌خطی"""

def test_html_details_summary():
    """تبدیل details/summary"""

# test_converter_md.py
def test_md_frontmatter_yaml():
    """تحلیل frontmatter YAML"""

def test_md_mermaid_to_component():
    """تبدیل بلوک mermaid به MermaidDiagram"""

def test_md_callouts():
    """تبدیل > [!NOTE] به Admonition"""

def test_md_task_list():
    """تبدیل task list"""

def test_md_definition_list():
    """تبدیل definition list"""

def test_md_footnotes():
    """تبدیل پانوشت‌ها"""

def test_md_jsx_compatibility():
    """بررسی سازگاری JSX (class→className, etc.)"""

# test_converter_docx.py
def test_docx_heading_levels():
    """تبدیل سطوح Heading"""

def test_docx_omml_to_latex():
    """تبدیل فرمول OMML به LaTeX"""

def test_docx_embedded_images():
    """استخراج تصاویر embed شده"""

def test_docx_rtl_paragraphs():
    """حفظ جهت RTL پاراگراف‌ها"""

# test_converter_pdf.py
def test_pdf_text_extraction():
    """استخراج متن از PDF متنی"""

def test_pdf_structure_detection():
    """تشخیص عناوین و پاراگراف‌ها"""

def test_pdf_table_extraction():
    """استخراج جداول"""

def test_pdf_image_extraction():
    """استخراج تصاویر embed شده"""

def test_pdf_formula_detection():
    """تشخیص و تبدیل فرمول‌ها"""

# test_persian.py
def test_zwnj_count_preserved():
    """شمارش ZWNJ قبل و بعد باید برابر باشد"""

def test_arabic_yeh_to_persian():
    """تبدیل ي به ی"""

def test_arabic_keh_to_persian():
    """تبدیل ك به ک"""

def test_guillemet_quotes():
    """بررسی استفاده از گیومه «»"""

def test_bidi_blocks():
    """بررسی صحت بلوک‌های LTR درون RTL"""

def test_persian_numerals():
    """تبدیل اعداد لاتین به فارسی (در صورت تنظیم)"""

def test_persian_typography_spacing():
    """بررسی فاصله‌گذاری صحیح فارسی"""

# test_quality.py
def test_quality_score_perfect_document():
    """سند بدون مشکل باید امتیاز >95 بگیرد"""

def test_quality_score_with_issues():
    """سند با مشکلات شناخته‌شده"""

def test_structural_validation():
    """اعتبارسنجی ساختار MDX"""

def test_link_validation():
    """اعتبارسنجی تمام لینک‌ها"""

# test_e2e.py (End-to-End)
def test_full_pipeline_latex_article():
    """تست کامل: مقاله LaTeX → MDX"""

def test_full_pipeline_latex_book():
    """تست کامل: کتاب LaTeX چندفصلی → MDX"""

def test_full_pipeline_html():
    """تست کامل: صفحه HTML → MDX"""

def test_full_pipeline_markdown():
    """تست کامل: فایل MD با Mermaid → MDX"""

def test_full_pipeline_docx():
    """تست کامل: فایل DOCX → MDX"""

def test_full_pipeline_zip():
    """تست کامل: فایل ZIP حاوی پروژه → MDX"""

def test_full_pipeline_mixed_folder():
    """تست کامل: پوشه ترکیبی → MDX"""


# فایل‌های تست (fixtures)
# tests/test_files/ حاوی نمونه‌هایی است که در ابتدای مکالمه ساختیم:
#   - sample-book.tex         (LaTeX جامع)
#   - sample-mermaid.md       (Markdown + Mermaid)
#   - sample-page.html        (HTML جامع)
#   - sample-page.rst         (RST)
#   - sample-page.adoc        (AsciiDoc)
#   - sample-book.docx        (DOCX)
#   - sample-book.pdf         (PDF)
```

```yaml
# .github/workflows/ci.yml  (یا معادل آن برای CI/CD محلی)

name: FormatForge CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: windows-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12"]

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install TeX Live
        run: |
          choco install texlive --params="'/scheme:full'"

      - name: Install Pandoc
        run: choco install pandoc

      - name: Install Node.js & Mermaid CLI
        uses: actions/setup-node@v4
        with:
          node-version: 20
      - run: npm install -g @mermaid-js/mermaid-cli

      - name: Install Python dependencies
        run: pip install -e ".[dev]"

      - name: Run tests
        run: pytest tests/ -v --cov=formatforge --cov-report=xml

      - name: Test with sample files
        run: |
          formatforge doctor
          formatforge convert tests/test_files/sample-book.tex --output tests/output/
          formatforge test tests/output/ --quality-min 85
```

---

## ۱۱. کامپوننت‌های MDX مورد نیاز در وب‌سایت

برای اینکه خروجی MDX به‌درستی در وب‌سایت رندر شود، کامپوننت‌های زیر باید در پروژه وب موجود باشند. ابزار FormatForge می‌تواند اسکلت این کامپوننت‌ها را تولید کند:

```bash
formatforge init-components --framework next --output ./components/mdx/
```

### ۱۱.۱ Theorem Component

```jsx
// components/mdx/Theorem.jsx
'use client';

const typeConfig = {
  theorem:    { label: 'قضیه',      labelEn: 'Theorem',    color: '#1A73E8', bg: '#E3F2FD' },
  lemma:      { label: 'لم',        labelEn: 'Lemma',      color: '#1565C0', bg: '#E3F2FD' },
  corollary:  { label: 'نتیجه',     labelEn: 'Corollary',  color: '#0D47A1', bg: '#E3F2FD' },
  conjecture: { label: 'حدس',       labelEn: 'Conjecture', color: '#4A148C', bg: '#F3E5F5' },
  axiom:      { label: 'اصل موضوع', labelEn: 'Axiom',      color: '#B71C1C', bg: '#FFEBEE' },
};

export default function Theorem({
  id,
  type = 'theorem',
  title,
  titleEn,
  number,
  children,
}) {
  const config = typeConfig[type] || typeConfig.theorem;

  return (
    <div
      id={id}
      dir="rtl"
      className="theorem-box"
      style={{
        background: config.bg,
        borderRight: `5px solid ${config.color}`,
        borderRadius: '0 8px 8px 0',
        padding: '1rem 1.5rem',
        margin: '1.5rem 0',
      }}
    >
      <div
        className="theorem-title"
        style={{
          fontWeight: 700,
          color: config.color,
          marginBottom: '0.5rem',
          fontSize: '1.05em',
        }}
      >
        {config.label}
        {number && ` ${number}`}
        {title && ` — ${title}`}
        {titleEn && (
          <span dir="ltr" style={{ fontSize: '0.9em', opacity: 0.8, marginRight: '0.5em' }}>
            ({titleEn})
          </span>
        )}
      </div>
      <div className="theorem-content">{children}</div>
    </div>
  );
}
```

### ۱۱.۲ Definition Component

```jsx
// components/mdx/Definition.jsx
export default function Definition({ id, title, titleEn, number, children }) {
  return (
    <div
      id={id}
      dir="rtl"
      className="definition-box"
      style={{
        background: '#E8F5E9',
        borderRight: '5px solid #00897B',
        borderRadius: '0 8px 8px 0',
        padding: '1rem 1.5rem',
        margin: '1.5rem 0',
      }}
    >
      <div style={{ fontWeight: 700, color: '#00897B', marginBottom: '0.5rem' }}>
        تعریف{number && ` ${number}`}
        {title && ` — ${title}`}
        {titleEn && (
          <span dir="ltr" style={{ fontSize: '0.9em', opacity: 0.8, marginRight: '0.5em' }}>
            ({titleEn})
          </span>
        )}
      </div>
      <div>{children}</div>
    </div>
  );
}
```

### ۱۱.۳ Proof Component

```jsx
// components/mdx/Proof.jsx
'use client';
import { useState } from 'react';

export default function Proof({ id, forRef, title = 'اثبات', collapsible = false, children }) {
  const [open, setOpen] = useState(!collapsible);

  const content = (
    <div
      id={id}
      className="proof-box"
      style={{
        background: '#FFFDE7',
        borderRight: '5px solid #FB8C00',
        borderRadius: '0 8px 8px 0',
        padding: '1rem 1.5rem',
        margin: '1.5rem 0',
      }}
    >
      <div style={{ fontWeight: 700, color: '#E65100', marginBottom: '0.5rem' }}>
        {title}
        {forRef && (
          <span style={{ fontSize: '0.9em', opacity: 0.8 }}>
            {' '}
            (برای <a href={`#${forRef}`}>↑</a>)
          </span>
        )}
      </div>
      <div>{children}</div>
      <div style={{ textAlign: 'left', fontSize: '1.2em', marginTop: '0.5rem' }}>∎</div>
    </div>
  );

  if (!collapsible) return content;

  return (
    <details open={open} onToggle={(e) => setOpen(e.target.open)}>
      <summary style={{ cursor: 'pointer', fontWeight: 700, color: '#E65100' }}>
        {open ? '🔽' : '▶️'} {title}
      </summary>
      {content}
    </details>
  );
}
```

### ۱۱.۴ Admonition Component

```jsx
// components/mdx/Admonition.jsx

const types = {
  note:      { icon: '📌', label: 'نکته',    color: '#546E7A', bg: '#ECEFF1' },
  tip:       { icon: '💡', label: 'راهنمایی', color: '#2E7D32', bg: '#E8F5E9' },
  info:      { icon: 'ℹ️', label: 'اطلاعات', color: '#1565C0', bg: '#E3F2FD' },
  warning:   { icon: '⚠️', label: 'هشدار',   color: '#EF6C00', bg: '#FFF3E0' },
  caution:   { icon: '🔶', label: 'احتیاط',  color: '#E65100', bg: '#FBE9E7' },
  danger:    { icon: '🚫', label: 'خطر',     color: '#C62828', bg: '#FFEBEE' },
  important: { icon: '❗', label: 'مهم',     color: '#6A1B9A', bg: '#F3E5F5' },
  example:   { icon: '📝', label: 'مثال',    color: '#7B1FA2', bg: '#F3E5F5' },
};

export default function Admonition({ type = 'note', title, children }) {
  const config = types[type] || types.note;
  const displayTitle = title || `${config.icon} ${config.label}`;

  return (
    <div
      dir="rtl"
      className={`admonition admonition-${type}`}
      style={{
        background: config.bg,
        borderRight: `5px solid ${config.color}`,
        borderRadius: '0 8px 8px 0',
        padding: '1rem 1.5rem',
        margin: '1.5rem 0',
      }}
    >
      <div style={{ fontWeight: 700, color: config.color, marginBottom: '0.5rem' }}>
        {displayTitle}
      </div>
      <div>{children}</div>
    </div>
  );
}
```

### ۱۱.۵ Figure Component

```jsx
// components/mdx/Figure.jsx
import Image from 'next/image';

export default function Figure({
  src,
  alt,
  caption,
  captionEn,
  number,
  width,
  height,
  float,       // "right" | "left" | undefined
  className,
}) {
  const floatStyle = float === 'right'
    ? { float: 'right', margin: '0 0 1rem 1.5rem', maxWidth: '40%' }
    : float === 'left'
    ? { float: 'left', margin: '0 1.5rem 1rem 0', maxWidth: '40%' }
    : {};

  return (
    <figure
      dir="rtl"
      className={`figure-box ${className || ''}`}
      style={{
        margin: '1.5rem 0',
        textAlign: 'center',
        ...floatStyle,
      }}
    >
      {src.endsWith('.svg') ? (
        // SVG: use img tag for better scaling
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={src}
          alt={alt}
          style={{
            maxWidth: '100%',
            borderRadius: '8px',
            boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
          }}
        />
      ) : (
        <Image
          src={src}
          alt={alt}
          width={width || 700}
          height={height || 400}
          style={{
            maxWidth: '100%',
            height: 'auto',
            borderRadius: '8px',
            boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
          }}
        />
      )}
      {(caption || number) && (
        <figcaption
          style={{
            color: '#616161',
            fontSize: '0.9em',
            marginTop: '0.5rem',
          }}
        >
          {number && <strong>شکل {number}. </strong>}
          {caption}
          {captionEn && (
            <span dir="ltr" style={{ opacity: 0.7, marginRight: '0.5em' }}>
              — {captionEn}
            </span>
          )}
        </figcaption>
      )}
    </figure>
  );
}
```

### ۱۱.۶ MermaidDiagram Component

```jsx
// components/mdx/MermaidDiagram.jsx
'use client';
import { useEffect, useRef, useState, useId } from 'react';

let mermaidModule = null;
const getMermaid = async () => {
  if (!mermaidModule) {
    mermaidModule = (await import('mermaid')).default;
    mermaidModule.initialize({
      startOnLoad: false,
      theme: 'base',
      themeVariables: {
        fontFamily: '"Vazirmatn", "Tahoma", sans-serif',
        fontSize: '14px',
        primaryColor: '#E3F2FD',
        primaryTextColor: '#0D47A1',
        primaryBorderColor: '#1565C0',
        lineColor: '#1A73E8',
      },
      flowchart: { htmlLabels: true, curve: 'basis' },
      sequence: { mirrorActors: false },
      securityLevel: 'loose',
    });
  }
  return mermaidModule;
};

export default function MermaidDiagram({ chart, id: propId, caption, number }) {
  const autoId = useId();
  const id = propId || `mermaid-${autoId.replace(/:/g, '')}`;
  const containerRef = useRef(null);
  const [svg, setSvg] = useState('');
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    const render = async () => {
      try {
        const mermaid = await getMermaid();
        const { svg: renderedSvg } = await mermaid.render(id, chart.trim());
        if (!cancelled) {
          setSvg(renderedSvg);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message || 'خطا در رندر نمودار');
          console.error('Mermaid render error:', err);
        }
      }
    };

    render();
    return () => { cancelled = true; };
  }, [chart, id]);

  if (error) {
    return (
      <div style={{
        background: '#FFEBEE', border: '1px solid #EF5350',
        borderRadius: 8, padding: '1rem', margin: '1.5rem 0',
        direction: 'ltr', textAlign: 'left',
      }}>
        <strong>⚠ خطا در رندر نمودار:</strong>
        <pre style={{ fontSize: '0.85em', marginTop: '0.5rem' }}>{error}</pre>
        <details>
          <summary>کد Mermaid</summary>
          <pre>{chart}</pre>
        </details>
      </div>
    );
  }

  return (
    <figure style={{ margin: '1.5rem 0', textAlign: 'center' }}>
      <div
        ref={containerRef}
        className="mermaid-container"
        style={{ direction: 'ltr', overflowX: 'auto' }}
        dangerouslySetInnerHTML={{ __html: svg }}
      />
      {(caption || number) && (
        <figcaption style={{ color: '#616161', fontSize: '0.9em', marginTop: '0.5rem' }}>
          {number && <strong>نمودار {number}. </strong>}
          {caption}
        </figcaption>
      )}
    </figure>
  );
}
```

### ۱۱.۷ Citation & Bibliography Components

```jsx
// components/mdx/Citation.jsx
export default function Citation({ id, data }) {
  // data = { author, year, title, ... } از bibliography.json
  return (
    <a
      href={`#ref-${id}`}
      className="citation"
      title={data ? `${data.author} (${data.year})` : id}
      style={{ color: '#00897B', textDecoration: 'none' }}
    >
      [{data ? `${data.author}, ${data.year}` : id}]
    </a>
  );
}

// components/mdx/Bibliography.jsx
export default function Bibliography({ entries }) {
  // entries = [{id, author, year, title, publisher, ...}, ...]
  return (
    <section id="bibliography" dir="rtl">
      <h2>📚 کتاب‌نامه</h2>
      <ol style={{ fontSize: '0.95em' }}>
        {entries.map((entry) => (
          <li key={entry.id} id={`ref-${entry.id}`}>
            {entry.lang === 'fa' ? (
              // مرجع فارسی
              <span>
                {entry.author} ({entry.year}).{' '}
                <cite style={{ fontStyle: 'italic' }}>{entry.title}</cite>.
                {entry.publisher && ` ${entry.publisher}.`}
              </span>
            ) : (
              // مرجع انگلیسی
              <span dir="ltr" lang="en">
                {entry.author} ({entry.year}).{' '}
                <cite style={{ fontStyle: 'italic' }}>{entry.title}</cite>.
                {entry.publisher && ` ${entry.publisher}.`}
                {entry.url && (
                  <>
                    {' '}
                    <a href={entry.url} target="_blank" rel="noopener noreferrer">
                      {new URL(entry.url).hostname}
                    </a>
                  </>
                )}
              </span>
            )}
          </li>
        ))}
      </ol>
    </section>
  );
}
```

### ۱۱.۸ CrossRef Component

```jsx
// components/mdx/CrossRef.jsx

const typeLabels = {
  theorem: 'قضیه',
  definition: 'تعریف',
  example: 'مثال',
  lemma: 'لم',
  figure: 'شکل',
  table: 'جدول',
  equation: 'رابطه',
  algorithm: 'الگوریتم',
  chapter: 'فصل',
  section: 'بخش',
};

export default function CrossRef({ id, type, number, text }) {
  const label = typeLabels[type] || '';
  const displayText = text || (label && number ? `${label} ${number}` : id);

  return (
    <a
      href={`#${id}`}
      className="cross-ref"
      style={{ color: '#1A73E8', textDecoration: 'none', borderBottom: '1px dashed #1A73E8' }}
    >
      {displayText}
    </a>
  );
}
```

### ۱۱.۹ BilingualBlock Component

```jsx
// components/mdx/BilingualBlock.jsx

export default function BilingualBlock({
  dir = 'ltr',
  lang = 'en',
  className,
  style,
  children,
}) {
  return (
    <div
      dir={dir}
      lang={lang}
      className={`bilingual-block ${className || ''}`}
      style={{
        background: dir === 'ltr' ? '#F5F5F5' : 'transparent',
        padding: dir === 'ltr' ? '1.5rem' : '0',
        borderRadius: '8px',
        borderLeft: dir === 'ltr' ? '4px solid #1A73E8' : 'none',
        borderRight: dir === 'rtl' ? '4px solid #1A73E8' : 'none',
        margin: '1.5rem 0',
        unicodeBidi: 'isolate',
        ...style,
      }}
    >
      {children}
    </div>
  );
}
```

### ۱۱.۱۰ تولید خودکار کامپوننت‌ها

```bash
# دستور تولید کامپوننت‌های MDX برای وب‌سایت شما
formatforge init-components \
  --framework next \
  --output ./components/mdx/ \
  --typescript \
  --with-css \
  --font "Vazirmatn" \
  --primary-color "#1A73E8" \
  --accent-color "#00897B"

# خروجی:
# components/mdx/
# ├── Theorem.tsx
# ├── Definition.tsx
# ├── Proof.tsx
# ├── Example.tsx
# ├── Admonition.tsx
# ├── Figure.tsx
# ├── FigureGrid.tsx
# ├── MermaidDiagram.tsx
# ├── Citation.tsx
# ├── Bibliography.tsx
# ├── CrossRef.tsx
# ├── BilingualBlock.tsx
# ├── CodeBlock.tsx
# ├── TableWrapper.tsx
# ├── Details.tsx
# ├── index.ts          ← re-exports همه
# └── styles/
#     ├── mdx-components.css
#     └── rtl-overrides.css
```

---

## ۱۲. نقشه راه توسعه (Roadmap)

```
فاز ۱ — MVP (هفته ۱-۴):
━━━━━━━━━━━━━━━━━━━━━━━━
☐ CLI پایه (scan, convert, test)
☐ تبدیل‌گر LaTeX → MDX (۸۰٪ عناصر)
☐ تبدیل‌گر Markdown → MDX
☐ مدیریت ریاضی (KaTeX)
☐ مدیریت فارسی/RTL/ZWNJ
☐ تست ساختاری و محتوایی
☐ استقرار ساده (کپی فایل)
☐ گزارش پایه

فاز ۲ — بهبود تبدیل (هفته ۵-۸):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
☐ تبدیل‌گر HTML → MDX
☐ تبدیل‌گر DOCX → MDX
☐ تبدیل‌گر RST → MDX
☐ تبدیل‌گر AsciiDoc → MDX
☐ TikZ → SVG
☐ Mermaid → کامپوننت
☐ جداول پیچیده (ادغامی/رنگی)
☐ کتاب‌نامه (biblatex → JSON)
☐ پوشش ۹۵٪+ عناصر LaTeX

فاز ۳ — هوشمندسازی (هفته ۹-۱۲):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
☐ تکمیل متادیتا با AI
☐ تولید slug هوشمند
☐ تولید خلاصه/description
☐ تولید alt text تصاویر
☐ پیشنهاد اصلاح خطاها
☐ تبدیل‌گر PDF → MDX (پایه)
☐ تبدیل‌گر EPUB → MDX
☐ تبدیل‌گر Jupyter → MDX

فاز ۴ — تست و کیفیت (هفته ۱۳-۱۶):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
☐ تست بصری (Playwright)
☐ مقایسه بصری خروجی با اصل
☐ امتیاز کیفیت پیشرفته
☐ گزارش HTML زیبا
☐ بهینه‌سازی عملکرد (parallel, cache)
☐ TUI با Textual

فاز ۵ — پیشرفته (هفته ۱۷+):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
☐ GUI (Tauri)
☐ Watch mode (تبدیل خودکار هنگام تغییر فایل)
☐ Plugin system (افزونه‌های سفارشی)
☐ API server (تبدیل از طریق HTTP)
☐ VS Code extension
☐ پشتیبانی از Typst
☐ تبدیل معکوس (MDX → LaTeX)
☐ انتشار به‌عنوان پکیج PyPI/npm
```

---

## ۱۳. مثال کامل: سناریوی واقعی

```
سناریو: تبدیل کتاب «مبانی منطق ریاضی» از LaTeX به MDX
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ورودی:
  D:\Code\Apps\formatforge\docs\logic-book\
  ├── main.tex              (نقطه ورود، 2 KB)
  ├── preamble.sty          (پکیج‌ها و تنظیمات، 3 KB)
  ├── chapter01.tex          (فصل ۱: مقدمه، 15 KB)
  ├── chapter02.tex          (فصل ۲: منطق گزاره‌ای، 22 KB)
  ├── chapter03.tex          (فصل ۳: منطق محمولات، 18 KB)
  ├── chapter04.tex          (فصل ۴: نمودارها، 12 KB)
  ├── chapter05.tex          (فصل ۵: راهنمای LaTeX، 8 KB)
  ├── references.bib         (کتاب‌نامه، 4 KB)
  └── figures/
      ├── mindmap.tikz       (نقشه ذهنی TikZ، 2 KB)
      ├── flowchart.tikz     (فلوچارت TikZ، 1.5 KB)
      ├── bar-chart.tikz     (نمودار میله‌ای، 1 KB)
      ├── proof-tree.tikz    (درخت اثبات، 1 KB)
      └── cover.png          (جلد کتاب، 500 KB)

دستور:
  formatforge run "D:\Code\Apps\formatforge\docs\logic-book\" \
    --output "C:\Projects\my-blog\content\books\" \
    --interactive

خروجی نهایی:
  C:\Projects\my-blog\content\books\logic-foundations\
  ├── _series.json
  ├── 00-introduction\
  │   ├── index.mdx          (11 KB)
  │   └── assets\
  │       └── mindmap.svg    (5 KB, از TikZ)
  ├── 01-propositional-logic\
  │   ├── index.mdx          (18 KB)
  │   └── assets\
  │       ├── truth-table-demorgan.svg  (3 KB)
  │       └── flowchart.svg            (4 KB)
  ├── 02-predicate-logic\
  │   ├── index.mdx          (14 KB)
  │   └── assets\
  │       └── proof-tree.svg (3 KB)
  ├── 03-visuals\
  │   ├── index.mdx          (10 KB)
  │   └── assets\
  │       ├── bar-chart.svg  (4 KB)
  │       └── cover.webp     (85 KB, بهینه از PNG)
  ├── 04-latex-guide\
  │   └── index.mdx          (7 KB)
  ├── bibliography.json       (3 KB, 15 مرجع)
  └── shared-assets\
      └── series-cover.webp  (85 KB)

آمار تبدیل:
  ⏱ زمان: ۱ دقیقه ۱۲ ثانیه
  📊 کیفیت: ۹۳/۱۰۰
  📄 فایل MDX: ۵ فصل
  🖼 تصاویر: ۶ SVG + ۱ WebP
  🔢 فرمول: ۸۷ (همه موفق)
  📊 جداول: ۱۲ (همه موفق)
  🎨 نمودار TikZ: ۵ → ۵ SVG
  📝 کد: ۸ بلوک
  📌 پانوشت: ۱۵
  🔗 ارجاعات: ۳۲ (۳۰ موفق, ۲ بین‌فصلی اصلاح‌شده)
  📚 مراجع: ۱۵ (biblatex → JSON)
  ‌ نیم‌فاصله: ۴۵۶/۴۵۶ ✅
```

---

## ۱۴. خلاصه نهایی و چک‌لیست ساخت

```
╔══════════════════════════════════════════════════════════════╗
║              FormatForge — چک‌لیست ساخت                     ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  ■ مرحله ۱: اسکن و شناسایی                                ║
║    ☐ تشخیص فرمت (magic bytes + extension + content)        ║
║    ☐ تشخیص encoding (UTF-8/BOM/Windows-1256)               ║
║    ☐ تشخیص ساختار (تک‌فایل/پوشه/ZIP/کتاب/مجموعه)          ║
║    ☐ تشخیص زبان (فارسی/انگلیسی/دوزبانه)                   ║
║    ☐ گراف وابستگی (include/input/images)                    ║
║    ☐ تأیید تعاملی از کاربر                                  ║
║                                                              ║
║  ■ مرحله ۲: متادیتا                                        ║
║    ☐ استخراج از ۹ فرمت مختلف                                ║
║    ☐ شِمای Pydantic برای اعتبارسنجی                        ║
║    ☐ تولید slug هوشمند (فارسی → لاتین)                     ║
║    ☐ تکمیل با AI (اختیاری)                                 ║
║    ☐ یکتایی slug (بررسی با گزارش مرکزی)                   ║
║    ☐ تأیید تعاملی                                          ║
║                                                              ║
║  ■ مرحله ۲.۵: پیش‌بررسی                                    ║
║    ☐ بررسی encoding و ZWNJ                                 ║
║    ☐ بررسی ساختار و syntax                                  ║
║    ☐ بررسی وابستگی‌ها (تصاویر/فایل‌ها)                     ║
║    ☐ بررسی فرمول‌ها (KaTeX pre-parse)                       ║
║    ☐ تبدیل آزمایشی (۱۰٪)                                  ║
║    ☐ تخمین زمان و حجم                                       ║
║    ☐ گزارش + تأیید                                          ║
║                                                              ║
║  ■ مرحله ۳: تبدیل                                          ║
║    ☐ ۹ تبدیل‌گر (LaTeX/HTML/MD/DOCX/PDF/RST/Adoc/EPUB/NB) ║
║    ☐ پردازشگر ریاضی (→ KaTeX syntax)                       ║
║    ☐ پردازشگر نمودار (TikZ→SVG, Mermaid→Component)        ║
║    ☐ پردازشگر جدول (ساده→MD, پیچیده→HTML)                 ║
║    ☐ پردازشگر تصویر (بهینه‌سازی/WebP/SVGO)                 ║
║    ☐ پردازشگر کد (syntax highlight metadata)               ║
║    ☐ پردازشگر لینک/ارجاع/پانوشت/کتاب‌نامه                ║
║    ☐ پردازشگر RTL/فارسی (ZWNJ/bidi/typography)            ║
║    ☐ تبدیل قضیه/تعریف/اثبات → کامپوننت                    ║
║    ☐ تولید import ها خودکار                                 ║
║    ☐ نمایش پیشرفت + خطاها                                   ║
║                                                              ║
║  ■ مرحله ۴: تست کیفیت                                      ║
║    ☐ تست ساختاری (YAML/JSX/MDX compile)                    ║
║    ☐ تست محتوایی (شمارش عناصر)                              ║
║    ☐ تست ریاضی (KaTeX parse)                               ║
║    ☐ تست فارسی (ZWNJ/bidi/quotes)                          ║
║    ☐ تست لینک‌ها (داخلی/خارجی/تصاویر)                      ║
║    ☐ تست بصری (Playwright — اختیاری)                        ║
║    ☐ امتیاز کیفیت (0-100)                                  ║
║                                                              ║
║  ■ مرحله ۵: استقرار                                        ║
║    ☐ ساخت ساختار پوشه                                       ║
║    ☐ کپی MDX + assets                                      ║
║    ☐ بهینه‌سازی تصاویر                                      ║
║    ☐ بروزرسانی لینک‌های نسبی                                ║
║    ☐ تولید فایل‌های جانبی (series.json, bibliography.json) ║
║    ☐ اعتبارسنجی نهایی                                      ║
║    ☐ Git commit (اختیاری)                                   ║
║                                                              ║
║  ■ مرحله ۶: گزارش                                          ║
║    ☐ ثبت در central_log                                     ║
║    ☐ آمار تجمعی                                              ║
║    ☐ ثبت slug (جلوگیری از تکرار)                           ║
║    ☐ خروجی YAML/JSON/CSV/HTML                               ║
║                                                              ║
║  ■ زیرساخت                                                   ║
║    ☐ CLI با Click + Rich                                    ║
║    ☐ تنظیمات YAML                                           ║
║    ☐ مدیریت خطا و بازیابی                                   ║
║    ☐ پردازش موازی                                            ║
║    ☐ کَش (TikZ, تصاویر, AI)                                ║
║    ☐ تست‌های واحد و E2E                                     ║
║    ☐ CI/CD                                                   ║
║    ☐ مستندسازی                                               ║
║    ☐ کامپوننت‌های MDX + init-components                     ║
║                                                              ║
╠══════════════════════════════════════════════════════════════╣
║  📝 نکات حیاتی فارسی:                                      ║
║    ▸ نیم‌فاصله (ZWNJ) هرگز حذف نشود                        ║
║    ▸ encoding همیشه UTF-8 (ترجیحاً BOM)                     ║
║    ▸ dir="rtl" + lang="fa" همیشه در frontmatter             ║
║    ▸ بلوک‌های کد/ریاضی/نمودار: dir="ltr"                   ║
║    ▸ گیومه «» نه ""                                         ║
║    ▸ شمارش ZWNJ قبل و بعد تبدیل باید برابر باشد           ║
║    ▸ ي→ی و ك→ک اصلاح شود                                  ║
╚══════════════════════════════════════════════════════════════╝
```

---

## ۱۵. نحوه استفاده از این پرامپت

### برای شروع توسعه:

```
این پرامپت را به یک LLM بدهید و بگویید:

"لطفاً بر اساس این مشخصات، کد ماژول [نام ماژول] را
بنویس. از Python 3.11+ استفاده کن. تست‌های واحد
هم بنویس."

مثال‌ها:
1. "کد core/scanner/file_detector.py را بنویس"
2. "کد core/converters/latex_to_mdx.py را بنویس"
3. "کد core/persian/zwnj_handler.py را بنویس"
4. "کد core/quality/math_test.py را بنویس"
5. "کد cli/commands/convert.py را بنویس"
```

### برای گسترش:

```
"بر اساس مشخصات پرامپت اصلی،
[قابلیت X] را اضافه کن / [بخش Y] را بهبود بده.
سازگاری با بقیه سیستم حفظ شود."
```

### Summary

---

## خلاصه

این پرامپت شامل **تمام** جزئیات فنی مورد نیاز برای ساخت ابزار تبدیل فرمت شماست:

| بخش | محتوا |
|:----|:------|
| **معماری** | ساختار ماژولار ۶ مرحله‌ای |
| **Stage 1** | اسکنر ورودی (۱۰ سناریو) + تأیید تعاملی |
| **Stage 2** | متادیتا (شِمای TypeScript + استخراج ۹ فرمت + AI + slug) |
| **Stage 2.5** | پیش‌بررسی (۵ دسته بررسی + تبدیل آزمایشی) |
| **Stage 3** | تبدیل (۹ فرمت × ۸+ پردازشگر + قواعد RTL/فارسی) |
| **Stage 4** | تست (۶ سطح + امتیاز کیفیت ۰-۱۰۰) |
| **Stage 5** | استقرار (ساختار پوشه + بهینه‌سازی + لینک‌دهی) |
| **Stage 6** | گزارش مرکزی YAML |
| **وابستگی‌ها** | Python packages + ابزارهای خارجی |
| **تنظیمات** | فایل YAML کامل با ۱۰۰+ آپشن |
| **CLI** | ۱۵+ دستور |
| **کامپوننت‌ها** | ۱۲ کامپوننت React/MDX |
| **تست** | ۴۰+ تست واحد + E2E + CI/CD |
| **نقشه راه** | ۵ فاز، ۱۷+ هفته |
| **نکات فارسی** | ۷ قانون حیاتی RTL/ZWNJ/bidi |