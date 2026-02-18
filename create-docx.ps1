# ============================================================
#  create-docx.ps1
#  ساخت فایل DOCX نمونه از Markdown با pandoc
# ============================================================

$OutputDir = "C:\Intel\formatforge\tests\test_files"
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$docxPath = (Resolve-Path $OutputDir).Path + "\sample-book-com.docx"

try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $doc = $word.Documents.Add()

    # --- تنظیمات RTL ---
    $doc.Content.ParagraphFormat.ReadingOrder = 0  # wdReadingOrderRtl
    $doc.Content.Font.Name = "B Nazanin"
    $doc.Content.Font.Size = 14

    # --- عنوان ---
    $range = $doc.Content
    $range.InsertAfter("مبانی منطق ریاضی و اثبات‌های صوری`n")
    $range.Paragraphs.Item(1).Style = "Heading 1"
    $range.InsertParagraphAfter()

    # --- زیرعنوان ---
    $range = $doc.Content
    $range.InsertAfter("Foundations of Mathematical Logic and Formal Proofs`n")
    $range.InsertParagraphAfter()

    # --- پاراگراف ---
    $range = $doc.Content
    $range.InsertAfter(
        "این سند به‌عنوان یک نمونه جامع تست طراحی شده " +
        "و شامل تمامی اجزای یک کتاب حرفه‌ای ریاضی–منطقی است.`n"
    )
    $range.InsertParagraphAfter()

    # --- تعریف ---
    $range = $doc.Content
    $range.InsertAfter("تعریف (گزاره):`n")
    $range.Paragraphs.Item($doc.Paragraphs.Count).Style = "Heading 2"
    $range.InsertParagraphAfter()

    $range = $doc.Content
    $range.InsertAfter(
        "گزاره جمله‌ای خبری است که دقیقاً یکی از دو " +
        "ارزش «درست» (True) یا «نادرست» (False) را دارد.`n"
    )
    $range.InsertParagraphAfter()

    # --- قضیه ---
    $range = $doc.Content
    $range.InsertAfter("قضیه (دمورگان):`n")
    $range.Paragraphs.Item($doc.Paragraphs.Count).Style = "Heading 2"
    $range.InsertParagraphAfter()

    $range = $doc.Content
    $range.InsertAfter("¬(p ∧ q) ≡ (¬p) ∨ (¬q)`n")
    $range.InsertParagraphAfter()

    # --- جدول ---
    $range = $doc.Content
    $range.InsertAfter("جدول ارزش:`n")
    $range.Paragraphs.Item($doc.Paragraphs.Count).Style = "Heading 3"
    $range.InsertParagraphAfter()

    $tableRange = $doc.Content
    $tableRange.Collapse(0) # wdCollapseEnd
    $table = $doc.Tables.Add($tableRange, 5, 4) # 5 rows x 4 cols
    $table.Borders.Enable = $true
    $table.Style = "Table Grid"

    # هدر
    $table.Cell(1,1).Range.Text = "p"
    $table.Cell(1,2).Range.Text = "q"
    $table.Cell(1,3).Range.Text = "¬(p∧q)"
    $table.Cell(1,4).Range.Text = "(¬p)∨(¬q)"

    # داده‌ها
    $data = @(
        @("T","T","F","F"),
        @("T","F","T","T"),
        @("F","T","T","T"),
        @("F","F","T","T")
    )
    for ($i = 0; $i -lt 4; $i++) {
        for ($j = 0; $j -lt 4; $j++) {
            $table.Cell($i+2, $j+1).Range.Text = $data[$i][$j]
        }
    }

    # --- ذخیره ---
    $doc.SaveAs2($docxPath, 16) # wdFormatXMLDocument = 16
    Write-Host "✅ فایل DOCX ساخته شد: $docxPath" -ForegroundColor Green

} catch {
    Write-Host "❌ خطا: $_" -ForegroundColor Red
} finally {
    if ($doc)  { $doc.Close($false) }
    if ($word) { $word.Quit() }
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null
}