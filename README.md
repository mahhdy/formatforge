# 🔄 FormatForge

**ابزار جامع تبدیل اسناد چندفرمتی به MDX — با پشتیبانی کامل فارسی**

> Comprehensive multi-format document converter to MDX with full Persian/RTL support.

## ✨ ویژگی‌ها

- 📄 پشتیبانی از LaTeX, Markdown, HTML, DOCX, PDF, RST, AsciiDoc
- 🔢 تبدیل کامل فرمول‌های ریاضی (KaTeX)
- 📊 تبدیل نمودارها (TikZ → SVG, Mermaid → Component)
- 🇮🇷 پشتیبانی کامل فارسی: RTL, نیم‌فاصله (ZWNJ), تایپوگرافی
- 🌐 محتوای دوزبانه (فارسی + انگلیسی)
- 🧪 تست کیفیت خودکار
- 📦 استقرار در وب‌سایت (Next.js, Astro, Gatsby)

## 🚀 شروع سریع

```bash
# نصب
pip install -e ".[all]"

# بررسی سلامت
formatforge doctor

# تبدیل
formatforge convert ./article.tex --output ./output/

# اجرای کامل
formatforge run ./input/ --output ./output/ --target ./website/content/
```
##  وضعیت توسعه

-  S01: زیرساخت ✅
-  S02: اسکنر
-  S03: ماژول فارسی
-  S04-S05: پردازشگرها
-  S06: Markdown → MDX
-  S07: HTML → MDX
-  S08-S09: LaTeX → MDX
-  S10: تست کیفیت
-  S11: استقرار و گزارش
-  S12: یکپارچه‌سازی

## 📜 مجوز

MIT License  