using PdfSharp.Fonts;

namespace PatientReports.DataServices;

// Core (non-GDI) PDFsharp needs an IFontResolver to supply font data.
// Maps the fonts we use to the corresponding Windows TrueType files.
public class WindowsFontResolver : IFontResolver
{
    private static readonly string FontsDir =
        Environment.GetFolderPath(Environment.SpecialFolder.Fonts);

    public byte[]? GetFont(string faceName)
    {
        // faceName is the file path we returned from ResolveTypeface.
        return File.Exists(faceName) ? File.ReadAllBytes(faceName) : null;
    }

    public FontResolverInfo ResolveTypeface(string familyName, bool isBold, bool isItalic)
    {
        // Default to Arial for any requested family (the reports only use Arial).
        string file =
            isBold && isItalic ? "arialbi.ttf" :
            isBold ? "arialbd.ttf" :
            isItalic ? "ariali.ttf" :
            "arial.ttf";

        var path = Path.Combine(FontsDir, file);
        return new FontResolverInfo(path);
    }
}
