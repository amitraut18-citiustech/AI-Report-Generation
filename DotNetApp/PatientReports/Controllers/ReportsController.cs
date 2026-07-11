using System.Text.Json;
using Microsoft.AspNetCore.Mvc;
using PatientReports.DataServices;
using PatientReports.Models;

namespace PatientReports.Controllers;

public class ReportsController : Controller
{
    private readonly PatientDataService _dataService;
    private readonly PdfReportService _pdfService;
    private readonly RdlRenderClient _rdlRenderClient;
    private readonly IWebHostEnvironment _env;
    private readonly IConfiguration _config;

    private static readonly JsonSerializerOptions JsonOpts = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase
    };

    public ReportsController(PatientDataService dataService, PdfReportService pdfService, RdlRenderClient rdlRenderClient, IWebHostEnvironment env, IConfiguration config)
    {
        _dataService = dataService;
        _pdfService = pdfService;
        _rdlRenderClient = rdlRenderClient;
        _env = env;
        _config = config;
    }

    // Resolves the existing plugin-generated HTML templates folder (no copies in
    // the project). Uses ReportForge:HtmlReportsPath (relative to content root),
    // falling back to an upward search for a HTMLReportsFolder directory.
    private string ResolveHtmlReportsDir()
    {
        var configured = _config["ReportForge:HtmlReportsPath"];
        if (!string.IsNullOrWhiteSpace(configured))
        {
            var path = Path.IsPathRooted(configured)
                ? configured
                : Path.GetFullPath(Path.Combine(_env.ContentRootPath, configured));
            if (Directory.Exists(path)) return path;
        }

        var dir = new DirectoryInfo(_env.ContentRootPath);
        while (dir != null)
        {
            var candidate = Path.Combine(dir.FullName, "HTMLReportsFolder");
            if (Directory.Exists(candidate)) return candidate;
            dir = dir.Parent;
        }

        throw new DirectoryNotFoundException(
            "Could not locate HTMLReportsFolder. Set ReportForge:HtmlReportsPath in appsettings.json.");
    }

    // Unified reports hub: a report dropdown + a single "Generate Report" button.
    // The selected report renders below the selector via the RdlView iframe.
    public IActionResult Index(string? report)
    {
        return View(new ReportsHubViewModel { SelectedReport = report });
    }

    // HTML-based reporting hub: proves the SSRS reports can be replaced by the
    // plugin-generated static HTML templates, populated by the existing .NET
    // data logic. The selected report renders in an iframe (the standalone
    // generated template served by HtmlReport).
    public IActionResult HtmlReports(string? report)
    {
        return View(new ReportsHubViewModel { SelectedReport = report });
    }

    // Serves a generated HTML template (from HtmlTemplates/) populated with
    // window.REPORT_DATA from the existing .NET data services. The report's
    // JavaScript is inlined so the page is fully self-contained.
    public async Task<IActionResult> HtmlReport(string report)
    {
        string key;
        object rows;
        object parameters = new { };

        switch (report)
        {
            case "patient":
                key = "patient";
                rows = await _dataService.GetPatientReportAsync();
                break;
            case "transplant":
                key = "transplant_event";
                rows = await _dataService.GetTransplantEventReportAsync();
                break;
            case "clinical":
                key = "patient_clinical_summary";
                rows = await _dataService.GetClinicalFlatRowsAsync();
                parameters = new { fromDate = "2026-01-01", toDate = "2026-12-31", status = "All", rptUser = User?.Identity?.Name ?? "system" };
                break;
            default:
                return RedirectToAction(nameof(HtmlReports));
        }

        var rowList = (System.Collections.ICollection)rows;
        var reportData = new
        {
            parameters,
            rows,
            narrative = "",
            meta = new
            {
                generatedAt = DateTime.UtcNow.ToString("o"),
                executedBy = User?.Identity?.Name ?? "system",
                rowCount = rowList.Count
            }
        };

        var dir = ResolveHtmlReportsDir();
        var html = await System.IO.File.ReadAllTextAsync(Path.Combine(dir, key + ".html"));
        var js = await System.IO.File.ReadAllTextAsync(Path.Combine(dir, key + ".js"));
        var json = JsonSerializer.Serialize(reportData, JsonOpts);

        // Inject the data at the marker and inline the report JS (self-contained).
        html = html.Replace("<!-- REPORT_DATA -->", $"<script>window.REPORT_DATA = {json};</script>");
        html = html.Replace($"<script src=\"{key}.js\" defer></script>", $"<script>{js}</script>");

        return Content(html, "text/html");
    }

    // Streams the selected report as a downloadable PDF file.
    public async Task<IActionResult> Download(string report)
    {
        byte[] pdf;
        string fileName;

        switch (report)
        {
            case "patient":
                pdf = _pdfService.PatientReport(await _dataService.GetPatientReportAsync());
                fileName = "PatientReport.pdf";
                break;
            case "transplant":
                pdf = _pdfService.TransplantEventReport(await _dataService.GetTransplantEventReportAsync());
                fileName = "TransplantEventReport.pdf";
                break;
            case "clinical":
                pdf = _pdfService.ClinicalSummary(await _dataService.GetClinicalSummaryAsync());
                fileName = "PatientClinicalSummary.pdf";
                break;
            default:
                return RedirectToAction(nameof(Index));
        }

        return File(pdf, "application/pdf", fileName);
    }

    // Renders the report from its real .rdl definition via RdlRenderService (see
    // that project for why RDL rendering can't run in-process on .NET 8), and
    // serves it inline (no Content-Disposition) for the <iframe> on the Reports
    // hub page.
    public async Task<IActionResult> RdlView(string report)
    {
        byte[] pdf;
        switch (report)
        {
            case "patient":
                pdf = await _rdlRenderClient.RenderAsync("patient", await _dataService.GetPatientReportAsync());
                break;
            case "transplant":
                pdf = await _rdlRenderClient.RenderAsync("transplant", await _dataService.GetTransplantEventReportAsync());
                break;
            case "clinical":
                var rows = await _dataService.GetClinicalFlatRowsAsync();
                var parameters = new Dictionary<string, string>
                {
                    ["FromDate"] = "2026-01-01",
                    ["ToDate"] = "2026-12-31",
                    ["Status"] = "All",
                    ["rptUser"] = User?.Identity?.Name ?? "system",
                };
                pdf = await _rdlRenderClient.RenderAsync("clinical", rows, parameters);
                break;
            default:
                return NotFound();
        }

        return File(pdf, "application/pdf");
    }

    // Kept for backward compatibility / direct links; both render the shared partials.
    public async Task<IActionResult> PatientReport()
    {
        var model = await _dataService.GetPatientReportAsync();
        return View(model);
    }

    public async Task<IActionResult> TransplantEventReport()
    {
        var model = await _dataService.GetTransplantEventReportAsync();
        return View(model);
    }
}
