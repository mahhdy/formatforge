.. meta::
   :description: نمونه جامع reStructuredText فارسی برای تست تبدیل به MDX
   :author: تیم تست
   :language: fa
   :dir: rtl

.. role:: fa
   :class: persian

.. role:: en
   :class: english

========================================
مبانی منطق ریاضی و اثبات‌های صوری
========================================

:نویسنده: مهدی سالم (Mahdi Salem)
:تاریخ: تابستان ۱۴۰۴
:نسخه: 1.0
:واژه‌های کلیدی: منطق، ریاضی، اثبات، دمورگان

.. contents:: فهرست مطالب
   :depth: 3
   :local:

----

مقدمه و مفاهیم پایه
====================

این سند به‌عنوان یک **نمونه جامع تست** طراحی شده و شامل تمامی
اجزای یک سند حرفه‌ای ریاضی-منطقی در فرمت
reStructuredText (:en:`RST`) است.

.. note::

   تمامی ارجاعات، پانوشت‌ها و کتاب‌نامه این سند صرفاً جهت تست هستند.
   برای مطالعه بیشتر به [Knuth1997]_ و [Ebrahimi1399]_ مراجعه کنید.

.. warning::

   این فایل باید با encoding **UTF-8** ذخیره شود.
   حتماً از ویرایشگری استفاده کنید که نیم‌فاصله (ZWNJ) را حفظ کند.

تعاریف
------

.. admonition:: تعریف ۱.۱ — گزاره (Proposition)

   **گزاره** جمله‌ای خبری است که دقیقاً یکی از دو ارزش
   «درست» (True, ⊤) یا «نادرست» (False, ⊥) را دارد.

   .. pull-quote::

      A *proposition* is a declarative sentence that is either
      **true** or **false**, but not both.

.. admonition:: تعریف ۱.۲ — تاتولوژی (Tautology)

   گزاره مرکب φ یک **تاتولوژی** است اگر و تنها اگر
   تحت *هر* تخصیص ارزش، مقدار آن درست (⊤) باشد.

   .. math::

      \models \varphi \iff \forall\, v : v(\varphi) = \top

قضایا و اثبات
--------------

.. admonition:: قضیه ۱.۱ — قانون دمورگان (De Morgan's Laws)
   :class: theorem

   برای هر دو گزاره :math:`p` و :math:`q`:

   .. math::

      \neg(p \land q) &\equiv (\neg p) \lor (\neg q) \\
      \neg(p \lor q)  &\equiv (\neg p) \land (\neg q)

.. admonition:: اثبات
   :class: proof

   اثبات را با جدول ارزش انجام می‌دهیم.
   جدول کامل در `جدول ارزش دمورگان`_ آمده است.
   با بررسی تمامی حالات، ستون‌های مربوطه برابرند. ∎

.. admonition:: مثال ۱.۱
   :class: example

   فرض کنید :math:`p`: «هوا بارانی است» و :math:`q`: «هوا سرد است».
   آنگاه:

   .. math::

      \neg(p \land q) \equiv \text{«هوا بارانی نیست \textbf{یا} سرد نیست»}

قضیه اصل طرد شق ثالث
~~~~~~~~~~~~~~~~~~~~~

.. admonition:: قضیه ۱.۲
   :class: theorem

   برای هر گزاره :math:`p`:

   .. math::

      \models\; p \lor \neg p

   این قضیه به **اصل طرد شق ثالث** (Law of Excluded Middle) معروف است. [#f1]_

.. admonition:: اثبات
   :class: proof

   دو حالت وجود دارد:

   - اگر :math:`p = \top`: آنگاه :math:`p \lor \neg p = \top \lor \bot = \top` ✅
   - اگر :math:`p = \bot`: آنگاه :math:`p \lor \neg p = \bot \lor \top = \top` ✅

   پس در هر دو حالت مقدار درست است. ∎

----

جدول ارزش و عملگرها
====================

.. _جدول ارزش دمورگان:

جدول ارزش دمورگان
------------------

.. table:: جدول ۱ — جدول ارزش قوانین دمورگان
   :widths: 10 10 20 25 10

   ===  ===  ================  =======================  ======
    p    q    ¬(p ∧ q)          (¬p) ∨ (¬q)             برابر؟
   ===  ===  ================  =======================  ======
    T    T    F                  F                        ✅
    T    F    T                  T                        ✅
    F    T    T                  T                        ✅
    F    F    T                  T                        ✅
   ===  ===  ================  =======================  ======

جدول عملگرهای منطقی
--------------------

.. csv-table:: جدول ۲ — عملگرهای منطقی پایه
   :header: "عملگر", "نماد", "نام انگلیسی", "مثال"
   :widths: 15, 10, 25, 15

   "نقیض", "¬", "Negation", "¬p"
   "عطف", "∧", "Conjunction", "p ∧ q"
   "فصل", "∨", "Disjunction", "p ∨ q"
   "شرطی", "→", "Implication", "p → q"
   "دوشرطی", "↔", "Biconditional", "p ↔ q"

جدول مقایسه سیستم‌های اثبات
----------------------------

.. list-table:: جدول ۳ — مقایسه سیستم‌های اثبات
   :header-rows: 1
   :widths: 20 15 10 10 20

   * - سیستم
     - نوع
     - تمامیت
     - سازگاری
     - کاربرد
   * - هیلبرت
     - اصل‌موضوعی
     - ✅
     - ✅
     - مبانی نظری
   * - استنتاج طبیعی
     - قاعده‌محور
     - ✅
     - ✅
     - آموزش
   * - تابلو
     - درختی
     - ✅
     - ✅
     - اثبات خودکار
   * - رزولوشن
     - مکانیزه
     - ✅ [#f2]_
     - ✅
     - SAT Solvers

----

فرمول‌های ریاضی
===============

فرمول درون‌خطی
--------------

قانون دمورگان: :math:`\neg(p \land q) \equiv (\neg p) \lor (\neg q)`

ماتریس
-------

.. math::

   A = \begin{pmatrix}
     a_{11} & a_{12} & \cdots & a_{1n} \\
     a_{21} & a_{22} & \cdots & a_{2n} \\
     \vdots & \vdots & \ddots & \vdots \\
     a_{m1} & a_{m2} & \cdots & a_{mn}
   \end{pmatrix}

مجموع و انتگرال
----------------

.. math::

   \sum_{k=0}^{\infty} \frac{x^k}{k!} = e^x
   ,\qquad
   \int_{-\infty}^{+\infty} e^{-x^2}\,dx = \sqrt{\pi}

فرمول‌های فیزیک (ماکسول)
-------------------------

.. math::

   \begin{aligned}
     \nabla \cdot \mathbf{E} &= \frac{\rho}{\epsilon_0}
       &\quad& \text{(قانون گاوس)} \\
     \nabla \cdot \mathbf{B} &= 0
       &\quad& \text{(نبود تک‌قطبی)} \\
     \nabla \times \mathbf{E} &= -\frac{\partial \mathbf{B}}{\partial t}
       &\quad& \text{(فاراده)} \\
     \nabla \times \mathbf{B} &= \mu_0 \mathbf{J}
       + \mu_0 \epsilon_0 \frac{\partial \mathbf{E}}{\partial t}
       &\quad& \text{(آمپر-ماکسول)}
   \end{aligned}

حالت‌ها (Cases)
---------------

.. math::

   |x| = \begin{cases}
     x  & \text{اگر } x \geq 0 \\
     -x & \text{اگر } x < 0
   \end{cases}

استقراء ریاضی
--------------

**قضیه:** برای هر :math:`n \in \mathbb{N}`:

.. math::

   \sum_{k=1}^{n} k = \frac{n(n+1)}{2}

**پایه:** :math:`n = 1`:

.. math::

   \sum_{k=1}^{1} k = 1 = \frac{1 \cdot 2}{2} \;\checkmark

**گام استقراء:**

.. math::

   \sum_{k=1}^{m+1} k = \frac{m(m+1)}{2} + (m+1) = \frac{(m+1)(m+2)}{2} \quad\blacksquare

----

کد و الگوریتم
=============

کد Python
---------

.. code-block:: python
   :linenos:
   :caption: بررسی تاتولوژی
   :name: lst-tautology

   from itertools import product

   def is_tautology(formula, variables):
       """Check if a propositional formula is a tautology."""
       for values in product([True, False], repeat=len(variables)):
           env = dict(zip(variables, values))
           if not formula(env):
               return False
       return True

   # Example: p ∨ ¬p
   result = is_tautology(
       lambda e: e['p'] or (not e['p']),
       ['p']
   )
   print(f"p ∨ ¬p is tautology: {result}")  # True

کد JavaScript
--------------

.. code-block:: javascript
   :linenos:
   :caption: بررسی قانون دمورگان

   function verifyDeMorgan(p, q) {
     const left  = !(p && q);
     const right = (!p) || (!q);
     return left === right;
   }

   for (const p of [true, false]) {
     for (const q of [true, false]) {
       console.log(`p=${p}, q=${q}: ${verifyDeMorgan(p, q)}`);
     }
   }

کد LaTeX
--------

.. code-block:: latex
   :caption: نمونه قضیه در LaTeX

   \begin{theorem}{قانون دمورگان}{demorgan}
     برای هر دو گزاره $p$ و $q$:
     \begin{align}
       \neg(p \land q) &\equiv (\neg p) \lor (\neg q) \\
       \neg(p \lor q)  &\equiv (\neg p) \land (\neg q)
     \end{align}
   \end{theorem}

کد Bash
-------

.. code-block:: bash
   :caption: کامپایل LaTeX

   # Compile with XeLaTeX
   xelatex -interaction=nonstopmode document.tex
   biber document
   xelatex -interaction=nonstopmode document.tex
   xelatex -interaction=nonstopmode document.tex

کد درون‌خطی
-----------

از تابع ``is_tautology()`` برای بررسی تاتولوژی استفاده کنید.
فایل اصلی در مسیر ``src/logic/evaluator.py`` قرار دارد.

----

تصاویر و رسانه
===============

تصویر ساده
-----------

.. figure:: https://via.placeholder.com/600x300/1A73E8/FFFFFF?text=Mathematical+Logic
   :alt: نمودار منطق ریاضی
   :width: 600px
   :align: center

   شکل ۱ — نمودار مفهومی منطق ریاضی

تصویر با لینک
--------------

.. figure:: https://via.placeholder.com/400x200/00897B/FFFFFF?text=Click+for+Wikipedia
   :alt: ویکی‌پدیا
   :target: https://en.wikipedia.org/wiki/Mathematical_logic
   :width: 400px
   :align: center

   شکل ۲ — کلیک کنید تا به ویکی‌پدیا بروید

----

لینک‌ها و ارجاعات
==================

لینک‌های خارجی
--------------

- `ویکی‌پدیا — منطق ریاضی <https://en.wikipedia.org/wiki/Mathematical_logic>`_
- `Stanford Encyclopedia — Classical Logic <https://plato.stanford.edu/entries/logic-classical/>`_
- `Mermaid Documentation <https://mermaid.js.org/>`_

ارجاعات متقاطع
---------------

- ارجاع به قضیه: `قضایا و اثبات`_
- ارجاع به جدول: `جدول ارزش دمورگان`_
- ارجاع به کد: :ref:`lst-tautology <lst-tautology>`

----

محتوای دوزبانه
===============

پاراگراف ترکیبی
-----------------

در منطق ریاضی (Mathematical Logic)، یک **گزاره** (Proposition)
جمله‌ای خبری است که دقیقاً یکی از دو ارزش **درست** (True, ⊤)
یا **نادرست** (False, ⊥) را دارد.

بلوک انگلیسی
-------------

.. container:: ltr-block

   **Definition (Tautology)**

   A compound proposition φ is a **tautology** if and only if it
   evaluates to **true** under every possible truth assignment:

   .. math::

      \models \varphi \iff \forall\, v : v(\varphi) = \top

   **Example:** :math:`p \lor \neg p` is a tautology
   (Law of Excluded Middle).

----

عناصر خاص RST
==============

نقل‌قول
-------

   «منطق آغاز خرد است، نه پایان آن.» — اسپاک

.. epigraph::

   In mathematics, you don't understand things.
   You just get used to them.

   -- John von Neumann

.. pull-quote::

   قضیه ناتمامیت گودل نشان می‌دهد که در هر سیستم صوری
   سازگار و به‌اندازه کافی قوی، گزاره‌های اثبات‌ناپذیر وجود دارند.

حاشیه‌نویسی (Sidebar)
-----------------------

.. sidebar:: واژه‌نامه سریع

   :تاتولوژی: همیشه درست
   :تناقض: همیشه نادرست
   :اقناع‌پذیر: گاهی درست

این متن در کنار حاشیه‌نویسی قرار می‌گیرد و نشان‌دهنده
عملکرد sidebar در reStructuredText است.

لیست تعاریف
-----------

تاتولوژی (Tautology)
   گزاره‌ای مرکب که تحت هر تخصیص ارزش، درست است.

تناقض (Contradiction)
   گزاره‌ای مرکب که تحت هر تخصیص ارزش، نادرست است.

اقناع‌پذیر (Satisfiable)
   گزاره‌ای مرکب که حداقل یک تخصیص ارزش آن را درست می‌کند.

لیست فیلدی
----------

:نام: مهدی سالم
:ایمیل: ali@example.com
:دانشگاه: دانشگاه تهران
:رشته: منطق ریاضی
:سال: ۱۴۰۴

.. topic:: نکته مهم

   در RST، عناصر ``topic``، ``sidebar``، ``admonition``
   و ``container`` همگی می‌توانند به کامپوننت‌های MDX
   تبدیل شوند.

.. tip::

   برای رندر صحیح ریاضیات در MDX، از KaTeX یا MathJax استفاده کنید.

.. danger::

   فونت فارسی در برخی محیط‌ها ممکن است به‌درستی نمایش داده نشود.
   حتماً encoding را بررسی کنید.

.. deprecated:: 2.0
   از ``old_function()`` استفاده نکنید. به‌جای آن از
   ``new_function()`` استفاده کنید.

.. versionadded:: 1.5
   پشتیبانی از منطق محمولات مرتبه اول اضافه شد.

.. versionchanged:: 2.0
   الگوریتم بررسی تاتولوژی بهینه شد.

جایگزینی متن
-------------

.. |date| date::
.. |time| date:: %H:%M

این سند در تاریخ |date| و ساعت |time| تولید شده است.

.. |logo| image:: https://via.placeholder.com/24x24/1A73E8/FFFFFF?text=L
   :alt: لوگو

این |logo| نشان‌دهنده لوگوی پروژه است.

----

پانوشت‌ها
=========

.. [#f1] اصل طرد شق ثالث (Law of Excluded Middle)
   در منطق شهودی (Intuitionistic Logic) پذیرفته نیست.

.. [#f2] فقط برای فرم نرمال عطفی (CNF).

.. [#f3] نیم‌فاصله (Zero-Width Non-Joiner, U+200C) کاراکتری نامرئی
   است که در فارسی بین پیشوند/پسوند و ریشه قرار می‌گیرد.

----

کتاب‌نامه
=========

.. [Knuth1997] Knuth, D. E. (1997). *The Art of Computer Programming*,
   Vol. 1, 3rd ed. Addison-Wesley.

.. [Godel1931] Gödel, K. (1931). "Über formal unentscheidbare Sätze
   der Principia Mathematica und verwandter Systeme I".
   *Monatshefte für Mathematik und Physik*, 38, 173–198.

.. [Ebrahimi1399] ابراهیمی، محمد (۱۳۹۹). *مبانی منطق ریاضی*.
   انتشارات دانشگاه تهران.

.. [MDN2024] MDN Web Docs (2024). "MathML".
   https://developer.mozilla.org/en-US/docs/Web/MathML

----

.. footer::

   ✍️ نویسنده: مهدی سالم |
   📅 تابستان ۱۴۰۴ |
   📜 مجوز: MIT