using MigraDoc.DocumentObjectModel;
using MigraDoc.DocumentObjectModel.Tables;
using MigraDoc.Rendering;
using PatientReports.Models;

namespace PatientReports.DataServices;

// Builds downloadable PDFs for the three reports using PDFsharp/MigraDoc (MIT).
public class PdfReportService
{
    private static readonly Color Brand = new Color(0xFF1F3864);
    private static readonly Color Band = new Color(0xFFDBE5F1);
    private static readonly Color RiskHigh = new Color(0xFFF8D7DA);
    private static readonly Color RiskLow = new Color(0xFFD1E7DD);

    public byte[] PatientReport(IReadOnlyList<PatientReportViewModel> rows)
    {
        var (doc, section) = NewDocument("Patient Report");

        var table = NewTable(section, 3.2, 3.2, 2.0, 3.0, 3.0, 5.5, 3.0);
        HeaderRow(table, "First Name", "Last Name", "Gender", "Date of Birth", "Contact", "Email", "Phone");
        foreach (var r in rows)
        {
            var row = table.AddRow();
            row.Cells[0].AddParagraph(r.FirstName);
            row.Cells[1].AddParagraph(r.LastName);
            row.Cells[2].AddParagraph(r.Gender);
            row.Cells[3].AddParagraph(r.DateOfBirth.ToShortDateString());
            row.Cells[4].AddParagraph(r.ContactNumber);
            row.Cells[5].AddParagraph(r.Email);
            row.Cells[6].AddParagraph(r.PhoneNumber);
        }

        return Render(doc);
    }

    public byte[] TransplantEventReport(IReadOnlyList<TransplantEventReportViewModel> rows)
    {
        var (doc, section) = NewDocument("Transplant Event Report");

        var banner = section.AddParagraph($"Total Transplants: {rows.Count}");
        banner.Format.Font.Bold = true;
        banner.Format.SpaceAfter = "6pt";

        var table = NewTable(section, 4.0, 2.4, 2.4, 2.4, 2.4, 2.6, 2.6, 1.6, 2.0);
        HeaderRow(table, "Patient", "Visit", "Prev Visit", "Transplant", "Infusion", "Event ID", "Tx Number", "Total", "Inpatient");
        foreach (var r in rows)
        {
            var row = table.AddRow();
            row.Cells[0].AddParagraph(r.PatientName);
            row.Cells[1].AddParagraph(r.DateOfVisit.ToShortDateString());
            row.Cells[2].AddParagraph(r.DateOfPreviousVisit.ToShortDateString());
            row.Cells[3].AddParagraph(r.TransplantDate.ToShortDateString());
            row.Cells[4].AddParagraph(r.InfusionDate.ToShortDateString());
            row.Cells[5].AddParagraph(r.EventId);
            row.Cells[6].AddParagraph(r.TransplantNumber);
            row.Cells[7].AddParagraph(rows.Count.ToString());
            row.Cells[8].AddParagraph(r.IsInpatient);
        }

        return Render(doc);
    }

    public byte[] ClinicalSummary(ClinicalSummaryViewModel model)
    {
        var (doc, section) = NewDocument("Patient Clinical Summary");

        // Facility summary aggregate table
        Heading(section, "Facility Summary");
        var summary = NewTable(section, 8.0, 2.5, 2.5, 2.5, 3.5, 4.0);
        HeaderRow(summary, "Facility", "# Patients", "# Events", "Avg Age", "Inpatient Events", "Out-of-range Labs");
        foreach (var f in model.Facilities)
        {
            var row = summary.AddRow();
            row.Cells[0].AddParagraph($"{f.FacilityName} ({f.City}, {f.State})");
            row.Cells[1].AddParagraph(f.PatientCount.ToString());
            row.Cells[2].AddParagraph(f.EventCount.ToString());
            row.Cells[3].AddParagraph(f.AvgAge.ToString());
            row.Cells[4].AddParagraph(f.InpatientEvents.ToString());
            var oor = row.Cells[5].AddParagraph(f.OutOfRangeLabs.ToString());
            oor.Format.Font.Bold = true;
            if (f.OutOfRangeLabs > 0) oor.Format.Font.Color = Colors.Red;
        }

        // Detail grouped Facility -> Patient -> Event -> Labs
        Heading(section, "Clinical Detail by Facility, Patient and Transplant Event");
        foreach (var f in model.Facilities)
        {
            var facBanner = section.AddParagraph($"Facility: {f.FacilityName} - {f.City}, {f.State}");
            facBanner.Format.Font.Bold = true;
            facBanner.Format.Font.Color = Brand;
            facBanner.Format.Shading.Color = Band;
            facBanner.Format.SpaceBefore = "10pt";
            facBanner.Format.SpaceAfter = "2pt";

            foreach (var p in f.Patients)
            {
                var pat = section.AddParagraph();
                pat.Format.Shading.Color = p.IsHighRisk ? RiskHigh : RiskLow;
                pat.Format.SpaceBefore = "4pt";
                pat.AddFormattedText(p.PatientName, TextFormat.Bold);
                pat.AddText($"   MRN: {p.MRN}   Age: {p.Age}   Sex: {p.Gender}   BMI: {p.BMI} ({p.BmiCategory})   Risk: {p.RiskScore}   Primary Dx: {p.PrimaryDiagnosis}   Active meds: {p.ActiveMedCount}");

                foreach (var e in p.Events)
                {
                    var ev = section.AddParagraph();
                    ev.Format.LeftIndent = "12pt";
                    ev.Format.SpaceBefore = "3pt";
                    ev.AddFormattedText(e.EventId, TextFormat.Bold);
                    ev.AddText($"   Visit: {e.DateOfVisit.ToShortDateString()}   Provider: {e.ProviderName} ({e.Specialty})   Donor: {e.DonorType}   {(e.IsInpatient ? "Inpatient" : "Outpatient")}   Days since previous visit: {e.DaysSincePreviousVisit}");

                    if (e.Labs.Count > 0)
                    {
                        var labs = NewTable(section, 8.0, 5.0, 6.0, 3.0);
                        HeaderRow(labs, "Test", "Result", "Reference", "Flag");
                        foreach (var l in e.Labs)
                        {
                            var row = labs.AddRow();
                            row.Cells[0].AddParagraph(l.TestName);
                            row.Cells[1].AddParagraph($"{l.Value} {l.Unit}");
                            row.Cells[2].AddParagraph($"{l.ReferenceLow} - {l.ReferenceHigh}");
                            var flag = row.Cells[3].AddParagraph(l.Flag);
                            flag.Format.Font.Bold = true;
                            flag.Format.Font.Color = l.IsOutOfRange ? Colors.Red : Colors.Green;
                            if (l.IsOutOfRange) row.Shading.Color = new Color(0xFFF8D7DA);
                        }
                    }
                    else
                    {
                        var none = section.AddParagraph("No lab results recorded for this event.");
                        none.Format.LeftIndent = "24pt";
                        none.Format.Font.Italic = true;
                        none.Format.Font.Color = Colors.Gray;
                        none.Format.Font.Size = 8;
                    }
                }
            }
        }

        return Render(doc);
    }

    // ---- helpers ----

    private static (Document, Section) NewDocument(string title)
    {
        var doc = new Document();
        var normal = doc.Styles["Normal"];
        normal.Font.Name = "Arial";
        normal.Font.Size = 9;

        var section = doc.AddSection();
        section.PageSetup.Orientation = Orientation.Landscape;
        section.PageSetup.PageFormat = PageFormat.A4;
        section.PageSetup.TopMargin = "1.5cm";
        section.PageSetup.BottomMargin = "1.5cm";
        section.PageSetup.LeftMargin = "1.5cm";
        section.PageSetup.RightMargin = "1.5cm";

        var t = section.AddParagraph(title);
        t.Format.Font.Size = 18;
        t.Format.Font.Bold = true;
        t.Format.Font.Color = Brand;

        var gen = section.AddParagraph($"Generated: {System.DateTime.Now:MM/dd/yyyy HH:mm}");
        gen.Format.Font.Size = 8;
        gen.Format.Font.Color = Colors.Gray;
        gen.Format.SpaceAfter = "8pt";

        var footer = section.Footers.Primary.AddParagraph();
        footer.Format.Alignment = ParagraphAlignment.Right;
        footer.Format.Font.Size = 8;
        footer.Format.Font.Color = Colors.Gray;
        footer.AddText("Page ");
        footer.AddPageField();
        footer.AddText(" of ");
        footer.AddNumPagesField();

        return (doc, section);
    }

    private static void Heading(Section section, string text)
    {
        var h = section.AddParagraph(text);
        h.Format.Font.Size = 13;
        h.Format.Font.Bold = true;
        h.Format.Font.Color = Brand;
        h.Format.SpaceBefore = "10pt";
        h.Format.SpaceAfter = "4pt";
    }

    private static Table NewTable(Section section, params double[] columnWidthsCm)
    {
        var table = section.AddTable();
        table.Borders.Width = 0.5;
        table.Borders.Color = Colors.LightGray;
        foreach (var w in columnWidthsCm)
            table.AddColumn(Unit.FromCentimeter(w));
        return table;
    }

    private static void HeaderRow(Table table, params string[] headers)
    {
        var row = table.AddRow();
        row.Shading.Color = Brand;
        row.Format.Font.Bold = true;
        row.Format.Font.Color = Colors.White;
        row.HeadingFormat = true; // repeat header on each page
        for (var i = 0; i < headers.Length; i++)
            row.Cells[i].AddParagraph(headers[i]);
    }

    private static byte[] Render(Document doc)
    {
        var renderer = new PdfDocumentRenderer { Document = doc };
        renderer.RenderDocument();
        using var ms = new MemoryStream();
        renderer.PdfDocument.Save(ms, false);
        return ms.ToArray();
    }
}
