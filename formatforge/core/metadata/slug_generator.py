"""
Slug Generator Module
ماژول تولید slug

Generates URL-friendly slugs from titles,
with Persian transliteration support.
"""

from __future__ import annotations

import re
from typing import Optional


# Persian to Latin character mappings (Finglish)
PERSIAN_TO_LATIN = {
    'ا': 'a', 'آ': 'a', 'ب': 'b', 'پ': 'p', 'ت': 't', 'ث': 's',
    'ج': 'j', 'چ': 'ch', 'ح': 'h', 'خ': 'kh', 'د': 'd', 'ذ': 'z',
    'ر': 'r', 'ز': 'z', 'ژ': 'zh', 'س': 's', 'ش': 'sh', 'ص': 's',
    'ض': 'z', 'ط': 't', 'ظ': 'z', 'ع': 'a', 'غ': 'gh', 'ف': 'f',
    'ق': 'q', 'ک': 'k', 'گ': 'g', 'ل': 'l', 'م': 'm', 'ن': 'n',
    'و': 'v', 'ه': 'h', 'ی': 'y', 'ۀ': 'h',
    # Numbers
    '۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4',
    '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9',
}

# Common Persian words to their Finglish equivalents
PERSIAN_WORDS = {
    'مبانی': 'mabani',
    'منطق': 'mantigh',
    'ریاضی': 'riyazi',
    'اثبات': 'esbat',
    'صوری': 'suri',
    'قضیه': 'ghaziyah',
    'تعریف': 'tarif',
    'لم': 'lam',
    'نتیجه': 'natije',
    'مثال': 'mesal',
    'اثبات': 'esbat',
    'برهان': 'borhan',
    'فصل': 'fasl',
    'مقدمه': 'moqaddameh',
    'کتاب': 'ketab',
    'مقاله': 'maqaleh',
    'درس': 'dars',
    'جزوه': 'jozeh',
    'آموزش': 'amuzesh',
    'راهنما': 'rahnameh',
    'قانون': 'ghanun',
    'اصل': 'asl',
    'حدس': 'hads',
    'فرض': 'farz',
    'شرط': 'shart',
    'نتیجه': 'natije',
    'اثبات': 'esbat',
    'برابر': 'barabar',
    'وارون': 'varun',
    'مجموعه': 'majmueh',
    'عضو': 'ozv',
    'تابع': 'tabe',
    'رابطه': 'rabeteh',
    'دامنه': 'dameh',
    'برد': 'bard',
    'هم‌ارز': 'ham-arz',
    'مزدوج': 'mozawaj',
    'وارون': 'varun',
    'وارونه': 'varuneh',
    'متقابل': 'motaqabel',
    'متقاطر': 'motaqater',
}


class SlugGenerator:
    """
    تولیدکننده slug.
    """
    
    def __init__(self, max_length: int = 60):
        """
        Args:
            max_length: حداکثر طول slug
        """
        self.max_length = max_length
        self._used_slugs: set[str] = set()
    
    def generate(
        self,
        title: str,
        lang: str = 'fa',
        existing_slugs: Optional[set[str]] = None,
    ) -> str:
        """
        تولید slug از عنوان.
        
        Args:
            title: عنوان سند
            lang: زبان (fa/en)
            existing_slugs: slugهای موجود برای بررسی تکراری
            
        Returns:
            slug یکتا
        """
        if existing_slugs:
            self._used_slugs = existing_slugs
        
        if lang == 'fa':
            slug = self._transliterate_persian(title)
        else:
            slug = self._slugify_english(title)
        
        slug = self._ensure_unique(slug)
        return slug
    
    def _transliterate_persian(self, text: str) -> str:
        """تبدیل متن فارسی به لاتین."""
        # First check for known words
        result = text
        for persian, latin in PERSIAN_WORDS.items():
            result = result.replace(persian, latin)
        
        # Then transliterate remaining characters
        slug_chars = []
        for char in result:
            if char in PERSIAN_TO_LATIN:
                slug_chars.append(PERSIAN_TO_LATIN[char])
            elif char.isalnum():
                slug_chars.append(char.lower())
            elif char in ' -_':
                slug_chars.append('-')
        
        slug = ''.join(slug_chars)
        slug = re.sub(r'-+', '-', slug)  # Multiple hyphens
        slug = slug.strip('-')
        
        # Truncate if too long
        if len(slug) > self.max_length:
            slug = slug[:self.max_length].rsplit('-', 1)[0]
        
        return slug or 'document'
    
    def _slugify_english(self, text: str) -> str:
        """تولید slug انگلیسی."""
        # Lowercase and replace spaces with hyphens
        slug = text.lower()
        slug = re.sub(r'[^\w\s-]', '', slug)  # Remove special chars
        slug = re.sub(r'[-\s]+', '-', slug)    # Replace spaces with -
        slug = slug.strip('-')
        
        # Truncate if too long
        if len(slug) > self.max_length:
            slug = slug[:self.max_length].rsplit('-', 1)[0]
        
        return slug or 'document'
    
    def _ensure_unique(self, slug: str) -> str:
        """اطمینان از یکتایی slug."""
        if slug not in self._used_slugs:
            self._used_slugs.add(slug)
            return slug
        
        # Add numeric suffix
        counter = 1
        while f"{slug}-{counter}" in self._used_slugs:
            counter += 1
        
        unique_slug = f"{slug}-{counter}"
        self._used_slugs.add(unique_slug)
        return unique_slug


# Convenience function
def generate_slug(title: str, lang: str = 'fa') -> str:
    """تولید slug ساده."""
    generator = SlugGenerator()
    return generator.generate(title, lang)
