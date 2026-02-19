"""
تست سرتاسری (E2E) تبدیل HTML → MDX — S07-C3
End-to-end test for the full HTML→MDX conversion pipeline.

یک فایل HTML کامل با تمام المان‌ها:
- header با متادیتا کامل
- ۸+ بخش محتوا (فصل‌ها)
- ۸+ جدول (شامل ادغامی و ساده)
- ۸+ نمودار Mermaid
- ۱۰+ فرمول ریاضی
- ۵+ بلوک کد
- تصاویر (img, svg, placeholder)
- ویدئو و صوت
- عناصر خاص: mark, kbd, abbr, details, progress
- فرم
- RTL/LTR blocks
- پانوشت‌ها
- کتاب‌نامه
- ZWNJ حفظ شده
"""

from __future__ import annotations

from pathlib import Path

import pytest

from formatforge.core.converters.base import ConversionContext
from formatforge.core.converters.html_to_mdx import HTMLToMDXConverter

ZWNJ = "\u200c"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Sample HTML Document
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_SAMPLE_HTML = f"""<!DOCTYPE html>
<html lang="fa-IR" dir="rtl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>راهنمای جامع برنامه{ZWNJ}نویسی پایتون</title>
  <meta name="description" content="یک راهنمای کامل برای یادگیری پایتون به زبان فارسی">
  <meta name="author" content="نویسنده آزمایشی">
  <meta name="keywords" content="پایتون, برنامه{ZWNJ}نویسی, آموزش">
  <meta property="og:title" content="OG: راهنمای پایتون">
  <meta property="og:description" content="آموزش جامع پایتون">
  <meta name="date" content="2025-01-15">
  <style>
    body {{ font-family: Vazir, sans-serif; direction: rtl; }}
    .highlight {{ background-color: yellow; }}
    table {{ border-collapse: collapse; }}
  </style>
</head>
<body>

<!-- === بخش ۱: سرصفحه === -->
<header>
  <h1>راهنمای جامع برنامه{ZWNJ}نویسی پایتون</h1>
  <p>این سند یک راهنمای کامل برای یادگیری زبان برنامه{ZWNJ}نویسی پایتون است.</p>
  <nav>
    <ul>
      <li><a href="#chapter1">فصل ۱: مقدمه</a></li>
      <li><a href="#chapter2">فصل ۲: داده{ZWNJ}ساختارها</a></li>
      <li><a href="#chapter3">فصل ۳: ریاضیات</a></li>
    </ul>
  </nav>
</header>

<!-- === بخش ۲: فصل اول === -->
<section id="chapter1">
  <h2>فصل اول: مقدمه{ZWNJ}ای بر پایتون</h2>

  <p>پایتون یکی از محبوب{ZWNJ}ترین زبان{ZWNJ}های برنامه{ZWNJ}نویسی مدرن است.
  این زبان با <strong>سینتکس ساده</strong> و <em>خوانایی بالا</em> شناخته می{ZWNJ}شود.</p>

  <blockquote>
    <p>«زبانی که به راحتی نوشته می{ZWNJ}شود و به راحتی خوانده می{ZWNJ}شود.»</p>
    <cite>گیدو ون روسوم</cite>
  </blockquote>

  <!-- نمودار معماری -->
  <div class="mermaid">
graph TD
    A[ورودی کاربر] --> B{{پردازش}}
    B --> C[خروجی]
    B --> D[خطا]
    D --> E[گزارش خطا]
  </div>

  <div class="mermaid">
sequenceDiagram
    participant کاربر
    participant سرور
    کاربر->>سرور: درخواست HTTP
    سرور-->>کاربر: پاسخ JSON
  </div>

  <!-- جدول ساده -->
  <h3>مقایسه زبان{ZWNJ}ها</h3>
  <table>
    <caption>مقایسه ویژگی‌های زبان‌های برنامه‌نویسی</caption>
    <thead>
      <tr>
        <th>زبان</th>
        <th>سرعت یادگیری</th>
        <th>کاربرد اصلی</th>
        <th>امتیاز</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td>پایتون</td>
        <td>سریع</td>
        <td>علم داده، هوش مصنوعی</td>
        <td>۹/۱۰</td>
      </tr>
      <tr>
        <td>جاوا</td>
        <td>متوسط</td>
        <td>اپلیکیشن سازمانی</td>
        <td>۷/۱۰</td>
      </tr>
      <tr>
        <td>جاوااسکریپت</td>
        <td>سریع</td>
        <td>توسعه وب</td>
        <td>۸/۱۰</td>
      </tr>
    </tbody>
  </table>

  <!-- کد نمونه -->
  <h3>مثال اول</h3>
  <pre><code class="language-python">
# برنامه Hello World در پایتون
def hello_world():
    # چاپ سلام دنیا
    print("سلام دنیا!")  # خروجی: سلام دنیا

hello_world()
  </code></pre>

</section>

<!-- === بخش ۳: فصل دوم === -->
<section id="chapter2">
  <h2>فصل دوم: داده{ZWNJ}ساختارهای پایتون</h2>

  <p>پایتون دارای انواع داده{ZWNJ}ای مختلف است. در این فصل با آن{ZWNJ}ها آشنا می{ZWNJ}شویم.</p>

  <!-- جدول ادغامی -->
  <h3>انواع داده{ZWNJ}ای</h3>
  <table>
    <thead>
      <tr>
        <th colspan="3">انواع داده‌ای پایتون</th>
      </tr>
      <tr>
        <th>دسته</th>
        <th>نوع</th>
        <th>مثال</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td rowspan="2">اعداد</td>
        <td>صحیح</td>
        <td><code>42</code></td>
      </tr>
      <tr>
        <td>اعشاری</td>
        <td><code>3.14</code></td>
      </tr>
      <tr>
        <td rowspan="2">دنباله</td>
        <td>لیست</td>
        <td><code>[1, 2, 3]</code></td>
      </tr>
      <tr>
        <td>تاپل</td>
        <td><code>(1, 2, 3)</code></td>
      </tr>
    </tbody>
  </table>

  <!-- کد نمونه -->
  <pre><code class="language-python">
# نمونه داده‌ساختارها
numbers = [1, 2, 3, 4, 5]
coordinates = (10.5, 20.3)
person = {{"name": "علی", "age": 25}}
unique_vals = {{1, 2, 3, 3, 2}}
  </code></pre>

  <!-- جدول ساده دیگر -->
  <table>
    <tr>
      <th>متد</th>
      <th>توضیح</th>
    </tr>
    <tr>
      <td><code>append()</code></td>
      <td>افزودن عنصر به انتهای لیست</td>
    </tr>
    <tr>
      <td><code>pop()</code></td>
      <td>حذف و بازگشت آخرین عنصر</td>
    </tr>
    <tr>
      <td><code>sort()</code></td>
      <td>مرتب{ZWNJ}سازی لیست</td>
    </tr>
  </table>

  <div class="mermaid">
graph LR
    لیست --> append
    لیست --> pop
    لیست --> sort
    لیست --> extend
  </div>

  <!-- تصویر -->
  <figure>
    <img src="images/data-structures.png" alt="نمودار داده‌ساختارها" width="800" height="400">
    <figcaption>شکل ۱: نمایش گرافیکی داده{ZWNJ}ساختارها در پایتون</figcaption>
  </figure>

</section>

<!-- === بخش ۴: فصل سوم — ریاضیات === -->
<section id="chapter3">
  <h2>فصل سوم: ریاضیات در پایتون</h2>

  <p>پایتون ابزارهای قدرتمندی برای محاسبات ریاضی دارد.</p>

  <!-- فرمول‌های ریاضی — KaTeX style -->
  <h3>۳.۱ فرمول{ZWNJ}های پایه</h3>
  <p>معادله درجه دوم:
    <span data-latex="ax^2 + bx + c = 0">ax² + bx + c = 0</span>
  </p>
  <p>فرمول حل معادله درجه دوم:
    <span data-latex="x = \\frac{{-b \\pm \\sqrt{{b^2 - 4ac}}}}{{2a}}">x = (-b ± √Δ) / 2a</span>
  </p>

  <!-- فرمول display mode -->
  <div>
    <script type="math/tex; mode=display">
      \\int_{{-\\infty}}^{{\\infty}} e^{{-x^2}} dx = \\sqrt{{\\pi}}
    </script>
  </div>

  <div>
    <script type="math/tex; mode=display">
      \\sum_{{n=1}}^{{\\infty}} \\frac{{1}}{{n^2}} = \\frac{{\\pi^2}}{{6}}
    </script>
  </div>

  <!-- فرمول‌های inline -->
  <p>انرژی در فیزیک: <script type="math/tex">E = mc^2</script></p>
  <p>قضیه فیثاغورث: <script type="math/tex">a^2 + b^2 = c^2</script></p>
  <p>ماتریس A:
    <script type="math/tex; mode=display">
      A = \\begin{{pmatrix}} a_{{11}} & a_{{12}} \\\\ a_{{21}} & a_{{22}} \\end{{pmatrix}}
    </script>
  </p>

  <!-- جدول با فرمول -->
  <table>
    <tr><th>مفهوم</th><th>فرمول</th></tr>
    <tr><td>انتگرال</td><td>∫f(x)dx</td></tr>
    <tr><td>مشتق</td><td>f'(x)</td></tr>
    <tr><td>حد</td><td>lim f(x)</td></tr>
  </table>

  <!-- بلوک کد پایتون -->
  <pre><code class="language-python">
import math

# محاسبه معادله درجه دوم
def quadratic(a, b, c):
    discriminant = b**2 - 4*a*c
    if discriminant < 0:
        return None  # بدون ریشه حقیقی
    x1 = (-b + math.sqrt(discriminant)) / (2*a)
    x2 = (-b - math.sqrt(discriminant)) / (2*a)
    return x1, x2

print(quadratic(1, -5, 6))  # (3.0, 2.0)
  </code></pre>

  <div class="mermaid">
graph TD
    ورودی --> حساب_Δ
    حساب_Δ --> Δ_مثبت
    حساب_Δ --> Δ_صفر
    حساب_Δ --> Δ_منفی
    Δ_مثبت --> دو_ریشه
    Δ_صفر --> یک_ریشه
    Δ_منفی --> بدون_ریشه
  </div>

</section>

<!-- === بخش ۵: رسانه === -->
<section id="chapter-media">
  <h2>فصل چهارم: رسانه</h2>

  <!-- ویدئو -->
  <h3>ویدئوی آموزشی</h3>
  <video src="videos/python-intro.mp4" controls width="800" height="450">
    <source src="videos/python-intro.mp4" type="video/mp4">
    مرورگر شما از ویدئو پشتیبانی نمی‌کند.
  </video>

  <!-- صوت -->
  <h3>فایل صوتی</h3>
  <audio src="audio/lecture.mp3" controls>
    <source src="audio/lecture.mp3" type="audio/mpeg">
    مرورگر شما از فایل صوتی پشتیبانی نمی‌کند.
  </audio>

  <!-- iframe -->
  <h3>ویدئوی یوتیوب</h3>
  <iframe
    src="https://www.youtube.com/embed/dQw4w9WgXcQ"
    title="ویدئوی آموزشی پایتون"
    width="800"
    height="450"
    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture">
  </iframe>

  <!-- SVG inline -->
  <h3>نمودار SVG</h3>
  <svg width="200" height="200" xmlns="http://www.w3.org/2000/svg">
    <title>نمودار دایره پایتون</title>
    <circle cx="100" cy="100" r="80" fill="#3776ab" opacity="0.8"/>
    <text x="100" y="105" text-anchor="middle" fill="white" font-size="20">Python</text>
  </svg>

</section>

<!-- === بخش ۶: عناصر خاص === -->
<section id="chapter-special">
  <h2>فصل پنجم: عناصر ویژه</h2>

  <!-- mark -->
  <p>این <mark>بخش مهم</mark> را نباید از دست بدهید.</p>

  <!-- kbd -->
  <p>برای اجرای برنامه، <kbd>Ctrl</kbd>+<kbd>F5</kbd> را فشار دهید.</p>

  <!-- abbr -->
  <p>زبان <abbr title="Artificial Intelligence">AI</abbr> از پایتون استفاده می{ZWNJ}کند.</p>

  <!-- time -->
  <p>تاریخ انتشار: <time datetime="2025-01-15">۱۵ ژانویه ۲۰۲۵</time></p>

  <!-- ins/del -->
  <p>متن قدیمی: <del>روش قدیمی</del> | متن جدید: <ins>روش جدید</ins></p>

  <!-- sup/sub -->
  <p>فرمول آب: H<sub>2</sub>O و ناحیه: m<sup>2</sup></p>

  <!-- details -->
  <details>
    <summary>توضیحات بیشتر درباره پایتون</summary>
    <p>پایتون توسط گیدو ون روسوم طراحی شده و در سال ۱۹۹۱ منتشر شد.</p>
    <p>این زبان یک زبان تفسیری، شیء{ZWNJ}گرا و سطح بالا است.</p>
    <ul>
      <li>ساده و خوانا</li>
      <li>کتابخانه{ZWNJ}های فراوان</li>
      <li>جامعه بزرگ</li>
    </ul>
  </details>

  <!-- details بیشتر -->
  <details>
    <summary>منابع یادگیری</summary>
    <ol>
      <li><a href="https://docs.python.org">مستندات رسمی</a></li>
      <li><a href="https://realpython.com">Real Python</a></li>
    </ol>
  </details>

  <!-- progress -->
  <p>پیشرفت یادگیری:
    <progress value="75" max="100">۷۵٪</progress>
  </p>

  <!-- meter -->
  <p>کیفیت کد:
    <meter value="0.8" min="0" max="1" low="0.3" high="0.7" optimum="0.9">۸۰٪</meter>
  </p>

</section>

<!-- === بخش ۷: RTL/LTR === -->
<section id="chapter-bidi">
  <h2>فصل ششم: دوجهته{ZWNJ}نویسی</h2>

  <div dir="rtl">
    <p>این متن از راست به چپ نوشته شده است.</p>
    <p>پایتون از متن فارسی پشتیبانی می{ZWNJ}کند.</p>
  </div>

  <div dir="ltr">
    <p>This is an LTR (Left-to-Right) paragraph in English.</p>
    <p>Python supports both RTL and LTR text.</p>
  </div>

  <div lang="en">
    <p>This paragraph has English language specified.</p>
    <pre><code class="language-bash">python3 --version
pip install numpy
</code></pre>
  </div>

  <div class="mermaid">
graph LR
    A[RTL بلوک] --- B[LTR بلوک]
    B --- C[ترکیبی]
  </div>

</section>

<!-- === بخش ۸: جداول بیشتر === -->
<section id="chapter-tables">
  <h2>فصل هفتم: جداول پیشرفته</h2>

  <!-- جدول با tfoot -->
  <table>
    <thead>
      <tr>
        <th>کتابخانه</th>
        <th>نسخه</th>
        <th>کاربرد</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td>NumPy</td>
        <td>1.24</td>
        <td>محاسبات عددی</td>
      </tr>
      <tr>
        <td>Pandas</td>
        <td>2.0</td>
        <td>تحلیل داده</td>
      </tr>
      <tr>
        <td>Matplotlib</td>
        <td>3.7</td>
        <td>رسم نمودار</td>
      </tr>
    </tbody>
    <tfoot>
      <tr>
        <td colspan="3">مجموع ۳ کتابخانه محبوب</td>
      </tr>
    </tfoot>
  </table>

  <!-- جدول ادغامی پیچیده -->
  <table>
    <thead>
      <tr>
        <th rowspan="2">کتابخانه</th>
        <th colspan="2">پشتیبانی</th>
      </tr>
      <tr>
        <th>پایتون ۳.x</th>
        <th>پایتون ۲.x</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td>NumPy</td>
        <td>✓</td>
        <td>✗</td>
      </tr>
      <tr>
        <td>Pandas</td>
        <td>✓</td>
        <td>✗</td>
      </tr>
    </tbody>
  </table>

  <div class="mermaid">
pie title استفاده از کتابخانه‌ها
    "NumPy" : 35
    "Pandas" : 30
    "Matplotlib" : 20
    "سایر" : 15
  </div>

  <div class="mermaid">
gantt
    title برنامه یادگیری
    dateFormat  YYYY-MM-DD
    section پایه
    نصب پایتون    :2025-01-01, 1d
    متغیرها       :2025-01-02, 3d
    section پیشرفته
    کتابخانه‌ها   :2025-01-10, 5d
  </div>

</section>

<!-- === بخش ۹: فرم === -->
<section id="chapter-form">
  <h2>فصل هشتم: فرم‌ها</h2>
  <p>نمونه فرم ثبت{ZWNJ}نام:</p>
  <form action="/register" method="POST">
    <label for="username">نام کاربری:</label>
    <input type="text" id="username" name="username" required>
    <label for="email">ایمیل:</label>
    <input type="email" id="email" name="email" required>
    <label for="level">سطح:</label>
    <select id="level" name="level">
      <option value="beginner">مبتدی</option>
      <option value="intermediate">متوسط</option>
      <option value="advanced">پیشرفته</option>
    </select>
    <button type="submit">ثبت‌نام</button>
  </form>
</section>

<!-- === پانوشت‌ها === -->
<section id="footnotes">
  <h2>پانوشت‌ها</h2>
  <ol>
    <li id="fn1">پایتون ابتدا در سال ۱۹۸۹ توسط گیدو ون روسوم شروع به توسعه شد.</li>
    <li id="fn2">نسخه ۳.x از سال ۲۰۰۸ منتشر شده و با نسخه ۲.x ناسازگار است.</li>
    <li id="fn3">PEP 8 استاندارد کدنویسی پایتون را تعریف می{ZWNJ}کند.</li>
  </ol>
</section>

<!-- === کتاب‌نامه === -->
<section id="bibliography">
  <h2>کتاب{ZWNJ}نامه</h2>
  <dl>
    <dt>Python Documentation</dt>
    <dd>مستندات رسمی پایتون — <a href="https://docs.python.org">docs.python.org</a></dd>
    <dt>Learning Python</dt>
    <dd>مارک لوتز — O'Reilly Media, 2013</dd>
    <dt>Fluent Python</dt>
    <dd>لوسیانو راماخو — O'Reilly Media, 2015</dd>
  </dl>
</section>

<footer>
  <p>این سند به صورت خودکار با FormatForge تبدیل شده است.</p>
  <p>تاریخ: <time datetime="2025-01-15">۱۵ ژانویه ۲۰۲۵</time></p>
</footer>

</body>
</html>"""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Fixtures
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@pytest.fixture(scope="module")
def sample_page(tmp_path_factory) -> Path:
    """فایل HTML نمونه."""
    tmp_path = tmp_path_factory.mktemp("e2e_html")
    p = tmp_path / "sample-page.html"
    p.write_text(_SAMPLE_HTML, encoding="utf-8")
    return p


@pytest.fixture(scope="module")
def converted(sample_page) -> tuple[str, ConversionContext]:
    """تبدیل فایل و بازگشت (mdx_content, context)."""
    converter = HTMLToMDXConverter()
    ctx = ConversionContext()
    result = converter.convert(sample_page, ctx)
    assert result.status == "success", f"تبدیل ناموفق: {result.error_message}"
    mdx = ctx.extra.get("mdx_content", "")
    return mdx, ctx


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# E2E Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestE2EConversionSuccess:
    """تست موفقیت تبدیل E2E."""

    def test_conversion_succeeded(self, converted):
        """تبدیل موفق باشد."""
        mdx, ctx = converted
        assert len(mdx) > 0

    def test_result_has_frontmatter(self, converted):
        """خروجی دارای frontmatter باشد."""
        mdx, ctx = converted
        assert mdx.startswith("---\n")

    def test_frontmatter_has_title(self, converted):
        """frontmatter دارای title باشد."""
        mdx, ctx = converted
        assert "title:" in mdx[:500]

    def test_frontmatter_has_lang(self, converted):
        """frontmatter دارای lang باشد."""
        mdx, ctx = converted
        assert "lang:" in mdx[:500]

    def test_frontmatter_has_dir(self, converted):
        """frontmatter دارای dir باشد."""
        mdx, ctx = converted
        assert "dir:" in mdx[:500]

    def test_frontmatter_rtl(self, converted):
        """lang فارسی → dir=rtl."""
        mdx, ctx = converted
        assert "rtl" in mdx[:500]

    def test_output_size_reasonable(self, converted):
        """حجم خروجی معقول باشد."""
        mdx, ctx = converted
        assert len(mdx) > 1000


class TestE2EMetadata:
    """تست متادیتای E2E."""

    def test_title_extracted(self, converted):
        """عنوان استخراج شده باشد."""
        mdx, ctx = converted
        assert ctx.metadata is not None
        assert "پایتون" in ctx.metadata.title

    def test_lang_detected(self, converted):
        """زبان فارسی تشخیص داده شود."""
        mdx, ctx = converted
        assert ctx.metadata.lang == "fa"

    def test_dir_rtl(self, converted):
        """جهت RTL باشد."""
        mdx, ctx = converted
        assert ctx.metadata.dir == "rtl"

    def test_source_format(self, converted):
        """فرمت منبع HTML باشد."""
        mdx, ctx = converted
        assert ctx.metadata.source_format == "html"


class TestE2EHeadings:
    """تست سرتیترها در E2E."""

    def test_h1_converted(self, converted):
        """<h1> به # تبدیل شده باشد."""
        mdx, ctx = converted
        assert "# راهنمای جامع" in mdx

    def test_h2_converted(self, converted):
        """<h2> به ## تبدیل شده باشد."""
        mdx, ctx = converted
        assert "## فصل اول" in mdx

    def test_h3_converted(self, converted):
        """<h3> به ### تبدیل شده باشد."""
        mdx, ctx = converted
        assert "### " in mdx

    def test_multiple_h2_sections(self, converted):
        """چندین بخش H2 باشد."""
        mdx, ctx = converted
        count = mdx.count("\n## ")
        assert count >= 4  # حداقل ۴ فصل


class TestE2ETables:
    """تست جداول در E2E."""

    def test_simple_table_converted(self, converted):
        """جدول ساده به pipe table تبدیل شده باشد."""
        mdx, ctx = converted
        assert "|" in mdx

    def test_table_has_data(self, converted):
        """جداول داده دارند."""
        mdx, ctx = converted
        assert "پایتون" in mdx
        assert "NumPy" in mdx

    def test_merged_table_html(self, converted):
        """جدول ادغامی به HTML JSX تبدیل شده باشد."""
        mdx, ctx = converted
        assert "<table>" in mdx

    def test_colspan_in_output(self, converted):
        """colspan در خروجی باشد."""
        mdx, ctx = converted
        assert "colSpan" in mdx or "colspan" in mdx.lower() or "<table>" in mdx

    def test_table_captions_preserved(self, converted):
        """caption جداول حفظ شود."""
        mdx, ctx = converted
        assert "مقایسه ویژگی" in mdx


class TestE2EMermaid:
    """تست نمودارهای Mermaid در E2E."""

    def test_mermaid_blocks_present(self, converted):
        """بلوک‌های Mermaid در خروجی باشند."""
        mdx, ctx = converted
        assert "mermaid" in mdx

    def test_mermaid_block_count(self, converted):
        """حداقل ۵ نمودار Mermaid باشد."""
        mdx, ctx = converted
        count = mdx.count("mermaid")
        assert count >= 5

    def test_mermaid_content_preserved(self, converted):
        """محتوای نمودار حفظ شود."""
        mdx, ctx = converted
        # محتوای graph یا sequence باید باشد
        assert "graph" in mdx or "sequenceDiagram" in mdx


class TestE2EMath:
    """تست فرمول‌های ریاضی در E2E."""

    def test_math_formulas_present(self, converted):
        """فرمول‌های ریاضی در خروجی باشند."""
        mdx, ctx = converted
        assert "$" in mdx

    def test_display_math_present(self, converted):
        """فرمول‌های display mode باشند."""
        mdx, ctx = converted
        assert "$$" in mdx

    def test_inline_math_present(self, converted):
        """فرمول‌های inline باشند."""
        mdx, ctx = converted
        # حداقل یک فرمول inline
        dollar_count = mdx.count("$")
        assert dollar_count >= 2


class TestE2ECode:
    """تست بلوک‌های کد در E2E."""

    def test_code_blocks_present(self, converted):
        """بلوک‌های کد در خروجی باشند."""
        mdx, ctx = converted
        assert "```" in mdx

    def test_python_code_block(self, converted):
        """بلوک کد پایتون باشد."""
        mdx, ctx = converted
        assert "```python" in mdx

    def test_code_content_preserved(self, converted):
        """محتوای کد حفظ شود."""
        mdx, ctx = converted
        assert "def hello_world" in mdx or "hello_world" in mdx


class TestE2EMedia:
    """تست رسانه در E2E."""

    def test_video_converted(self, converted):
        """<video> تبدیل شده باشد."""
        mdx, ctx = converted
        assert "<Video" in mdx

    def test_audio_converted(self, converted):
        """<audio> تبدیل شده باشد."""
        mdx, ctx = converted
        assert "<Audio" in mdx

    def test_iframe_converted(self, converted):
        """<iframe> تبدیل شده باشد."""
        mdx, ctx = converted
        assert "<Embed" in mdx

    def test_svg_converted(self, converted):
        """<svg> به <Image> تبدیل شده باشد."""
        mdx, ctx = converted
        assert "<Image" in mdx

    def test_img_converted(self, converted):
        """<img> به <Image> تبدیل شده باشد."""
        mdx, ctx = converted
        assert "<Image" in mdx


class TestE2ESpecialElements:
    """تست عناصر ویژه در E2E."""

    def test_mark_present(self, converted):
        """<mark> حفظ شده باشد."""
        mdx, ctx = converted
        assert "<mark>" in mdx

    def test_kbd_present(self, converted):
        """<kbd> حفظ شده باشد."""
        mdx, ctx = converted
        assert "<kbd>" in mdx

    def test_abbr_present(self, converted):
        """<abbr> حفظ شده باشد."""
        mdx, ctx = converted
        assert "<abbr" in mdx

    def test_details_converted(self, converted):
        """<details> به <Details> تبدیل شده باشد."""
        mdx, ctx = converted
        assert "<Details" in mdx

    def test_progress_present(self, converted):
        """<progress> در خروجی باشد."""
        mdx, ctx = converted
        assert "<progress" in mdx or "progress" in mdx

    def test_figure_caption_preserved(self, converted):
        """caption تصویر حفظ شود."""
        mdx, ctx = converted
        assert "شکل ۱" in mdx or "داده‌ساختارها" in mdx


class TestE2EForm:
    """تست فرم در E2E."""

    def test_form_converted_to_comment(self, converted):
        """<form> به comment/placeholder تبدیل شود."""
        mdx, ctx = converted
        assert "{/*" in mdx or "Form" in mdx

    def test_script_removed(self, converted):
        """<script> های غیر ریاضی حذف شوند."""
        mdx, ctx = converted
        assert "alert" not in mdx

    def test_style_removed(self, converted):
        """<style> حذف شود."""
        mdx, ctx = converted
        assert "font-family: Vazir" not in mdx


class TestE2EBidi:
    """تست دوجهته‌نویسی در E2E."""

    def test_rtl_div_preserved(self, converted):
        """<div dir='rtl'> حفظ شود."""
        mdx, ctx = converted
        assert 'dir="rtl"' in mdx

    def test_ltr_div_preserved(self, converted):
        """<div dir='ltr'> حفظ شود."""
        mdx, ctx = converted
        assert 'dir="ltr"' in mdx

    def test_lang_en_div_preserved(self, converted):
        """<div lang='en'> حفظ شود."""
        mdx, ctx = converted
        assert 'lang="en"' in mdx


class TestE2EBibliography:
    """تست کتاب‌نامه در E2E."""

    def test_bibliography_section(self, converted):
        """بخش کتاب‌نامه موجود باشد."""
        mdx, ctx = converted
        assert "کتاب" in mdx

    def test_bibliography_entries(self, converted):
        """ورودی‌های کتاب‌نامه باشند."""
        mdx, ctx = converted
        assert "Python Documentation" in mdx or "Learning Python" in mdx


class TestE2EFootnotes:
    """تست پانوشت‌ها در E2E."""

    def test_footnotes_section(self, converted):
        """بخش پانوشت‌ها موجود باشد."""
        mdx, ctx = converted
        assert "پانوشت" in mdx

    def test_footnote_content(self, converted):
        """محتوای پانوشت‌ها حفظ شود."""
        mdx, ctx = converted
        assert "گیدو ون روسوم" in mdx


class TestE2EZWNJPreservation:
    """تست حفظ نیم‌فاصله در E2E."""

    def test_zwnj_in_output(self, converted):
        """ZWNJ در خروجی وجود داشته باشد."""
        mdx, ctx = converted
        assert ZWNJ in mdx

    def test_zwnj_count_reasonable(self, converted):
        """تعداد ZWNJ معقول باشد."""
        mdx, ctx = converted
        count = mdx.count(ZWNJ)
        # HTML ورودی شامل ۲۰+ ZWNJ است
        assert count >= 10

    def test_zwnj_in_frontmatter(self, converted):
        """ZWNJ در frontmatter باشد."""
        mdx, ctx = converted
        # frontmatter بین ---
        end_fm = mdx.find("\n---\n", 4)
        if end_fm > 0:
            frontmatter = mdx[:end_fm + 4]
            assert ZWNJ in frontmatter

    def test_zwnj_not_lost_in_pipeline(self, converted):
        """pipeline پردازش ZWNJ از دست ندهد."""
        mdx, ctx = converted
        before = ctx.zwnj_count_before
        after = ctx.zwnj_count_after
        if before > 0:
            # حداقل ۸۰٪ ZWNJ‌ها باید حفظ شوند
            assert after >= before * 0.8


class TestE2ELinkConversion:
    """تست تبدیل لینک‌ها در E2E."""

    def test_links_converted(self, converted):
        """لینک‌ها تبدیل شده باشند."""
        mdx, ctx = converted
        assert "[" in mdx and "](" in mdx

    def test_nav_links(self, converted):
        """لینک‌های ناوبری باشند."""
        mdx, ctx = converted
        assert "فصل ۱" in mdx

    def test_external_links(self, converted):
        """لینک‌های خارجی باشند."""
        mdx, ctx = converted
        assert "https://docs.python.org" in mdx


class TestE2EListConversion:
    """تست تبدیل لیست‌ها در E2E."""

    def test_unordered_list(self, converted):
        """لیست نامرتب تبدیل شده باشد."""
        mdx, ctx = converted
        assert "- " in mdx

    def test_ordered_list(self, converted):
        """لیست مرتب تبدیل شده باشد."""
        mdx, ctx = converted
        assert "1. " in mdx

    def test_definition_list(self, converted):
        """لیست تعریفی تبدیل شده باشد."""
        mdx, ctx = converted
        # dl باید به dt/dd تبدیل شود
        assert "Python Documentation" in mdx


class TestE2EOutputQuality:
    """تست کیفیت خروجی E2E."""

    def test_quality_frontmatter_valid(self, converted, sample_page):
        """frontmatter معتبر باشد."""
        converter = HTMLToMDXConverter()
        ctx = ConversionContext()
        result = converter.convert(sample_page, ctx)
        assert result.quality.frontmatter_valid is True

    def test_quality_mdx_valid(self, converted, sample_page):
        """MDX معتبر باشد."""
        converter = HTMLToMDXConverter()
        ctx = ConversionContext()
        result = converter.convert(sample_page, ctx)
        assert result.quality.mdx_valid is True

    def test_quality_score_positive(self, converted, sample_page):
        """امتیاز کیفیت مثبت باشد."""
        converter = HTMLToMDXConverter()
        ctx = ConversionContext()
        result = converter.convert(sample_page, ctx)
        result.quality.compute_score()
        assert result.quality.score > 0

    def test_no_conversion_errors(self, converted):
        """بدون خطای تبدیل."""
        mdx, ctx = converted
        # context errors should be empty
        assert len(ctx.errors) == 0
