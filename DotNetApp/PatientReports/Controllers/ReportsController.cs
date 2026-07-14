using System.Text.Json;
using Microsoft.AspNetCore.DataProtection;
using Microsoft.AspNetCore.Mvc;
using PatientReports.DataServices;
using PatientReports.Models;

namespace PatientReports.Controllers;

public class ReportsController : Controller
{
    private readonly PatientDataService _dataService;
    private readonly PdfReportService _pdfService;
    private readonly RdlRenderClient _rdlRenderClient;
    private readonly ReportBrainClient _brainClient;
    private readonly ReportQueryService _queryService;
    private readonly IWebHostEnvironment _env;
    private readonly IConfiguration _config;
    private readonly ILogger<ReportsController> _logger;
    private readonly IDataProtector _specProtector;

    private static readonly JsonSerializerOptions JsonOpts = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        PropertyNameCaseInsensitive = true
    };

    public ReportsController(PatientDataService dataService, PdfReportService pdfService, RdlRenderClient rdlRenderClient, ReportBrainClient brainClient, ReportQueryService queryService, IWebHostEnvironment env, IConfiguration config, ILogger<ReportsController> logger, IDataProtectionProvider dataProtection)
    {
        _specProtector = dataProtection.CreateProtector("ReportForge.QuerySpec");
        _dataService = dataService;
        _pdfService = pdfService;
        _rdlRenderClient = rdlRenderClient;
        _brainClient = brainClient;
        _queryService = queryService;
        _env = env;
        _config = config;
        _logger = logger;
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

    /// <summary>
    /// Encode a QuerySpec to a tamper-proof, URL-safe string for query-string
    /// transport. The payload is signed+encrypted via Data Protection so
    /// clients cannot craft arbitrary filters against the database.
    /// </summary>
    private string EncodeQuerySpec(QuerySpec spec)
    {
        var json = JsonSerializer.Serialize(spec, JsonOpts);
        return _specProtector.Protect(json);
    }

    /// <summary>
    /// Decode a protected QuerySpec from a query-string parameter.
    /// Returns null if the input is missing, tampered with, or malformed.
    /// </summary>
    private QuerySpec? DecodeQuerySpec(string? spec)
    {
        if (string.IsNullOrWhiteSpace(spec)) return null;
        try
        {
            var json = _specProtector.Unprotect(spec);
            return JsonSerializer.Deserialize<QuerySpec>(json, JsonOpts);
        }
        catch
        {
            _logger.LogWarning("Failed to decode spec query parameter (invalid or tampered)");
            return null;
        }
    }

    /// <summary>
    /// Maps a brain report key to the primary EF Core table name, used to
    /// default any filter that lacks an explicit table.
    /// </summary>
    private static string PrimaryTableForReport(string brainReport)
    {
        return brainReport switch
        {
            "transplant_event" => "TransplantEvents",
            "patient_clinical_summary" => "TransplantEvents",
            _ => "Patients",
        };
    }

    // Unified reports hub: a report dropdown + a single "Generate Report" button.
    // The selected report renders below the selector via the RdlView iframe.
    // fromDate/toDate only apply to the transplant report's visit-date filter.
    public IActionResult Index(string? report, string? fromDate, string? toDate, string? minAge, string? maxAge)
    {
        return View(new ReportsHubViewModel
        {
            SelectedReport = report,
            FromDate = fromDate ?? "2026-01-01",
            ToDate = toDate ?? "2026-12-31",
            MinAge = minAge ?? "18",
            MaxAge = maxAge ?? "70",
        });
    }

    // HTML-based reporting hub: proves the SSRS reports can be replaced by the
    // plugin-generated static HTML templates, populated by the existing .NET
    // data logic. The selected report renders in an iframe (the standalone
    // generated template served by HtmlReport).
    public IActionResult HtmlReports(string? report, string? question, string? brainError, string? spec, string? decodedBy)
    {
        var vm = new ReportsHubViewModel
        {
            SelectedReport = report,
            Question = question,
            BrainError = brainError,
            QuerySpecB64 = spec,
            DecodedBy = decodedBy,
        };

        // Decode the spec to display the applied-filters badges in the hub page.
        var querySpec = DecodeQuerySpec(spec);
        if (querySpec != null)
            vm.AppliedFilters = querySpec.Filters;

        return View(vm);
    }

    // Transparency page: shows what was actually sent to each LLM (original
    // question vs. scrubbed question / anonymized rows), fetched from the
    // brain's in-memory prompt log. Populated by the two Ask buttons.
    public async Task<IActionResult> PromptLog()
    {
        var vm = new PromptLogViewModel();
        try
        {
            var log = await _brainClient.GetPromptLogAsync();
            vm.Entries = log.Entries;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to fetch prompt log from brain");
            vm.Error = "The AI brain service is unavailable — the prompt log lives there.";
        }
        return View(vm);
    }

    public async Task<IActionResult> AskReport(string question, string provider = "local")
    {
        if (string.IsNullOrWhiteSpace(question))
            return RedirectToAction(nameof(HtmlReports));

        // The brain owns the Claude API key (ai-report-forge/.env). "claude"
        // decodes directly on the Claude API; "local" uses Ollama with an
        // automatic Claude fallback when configured. If Claude is not
        // configured the brain returns UNKNOWN with an explanatory message,
        // which surfaces below as brainError.
        if (provider != "claude")
            provider = "local";

        try
        {
            var decoded = await _brainClient.DecodePromptAsync(question, provider);

            if (decoded.Report == "UNKNOWN" || decoded.Confidence < 0.3)
            {
                var msg = decoded.Message ?? "No matching report found for your question.";
                return RedirectToAction(nameof(HtmlReports), new { brainError = msg, question });
            }

            var reportKey = MapDecodedReport(decoded.Report);
            if (reportKey == null)
            {
                return RedirectToAction(nameof(HtmlReports), new
                {
                    brainError = $"Brain identified report '{decoded.Report}' but it is not available in the app.",
                    question
                });
            }

            // Merge top-level filters into Query (handles older brain versions
            // that return filters outside the query object) and default any
            // filter with a missing table to the primary entity.
            decoded.NormalizeFilters(PrimaryTableForReport(decoded.Report));

            // Pass the query spec as a Base64-encoded query parameter so it
            // survives the redirect chain and reaches the iframe request.
            // TempData (cookie-based) was unreliable here because the iframe's
            // HTTP request fires before the browser processes the Set-Cookie
            // from the hub page response.
            string? specB64 = null;
            if (decoded.Query.Filters.Count > 0)
                specB64 = EncodeQuerySpec(decoded.Query);

            return RedirectToAction(nameof(HtmlReports), new { report = reportKey, question, spec = specB64, decodedBy = decoded.Source });
        }
        catch (Exception ex)
        {
            // Do not log the question text — it can contain PHI (patient names).
            _logger.LogError(ex, "Brain service call failed");
            return RedirectToAction(nameof(HtmlReports), new
            {
                brainError = "AI brain service is unavailable. Please select a report from the dropdown.",
                question
            });
        }
    }

    private static string? MapDecodedReport(string brainReport)
    {
        return brainReport switch
        {
            "patient" => "patient",
            "patient_demographics" => "patient",
            "blood_type_distribution" => "patient",
            "transplant_event" => "transplant",
            "patient_clinical_summary" => "clinical",
            _ => null,
        };
    }

    // Serves a generated HTML template (from HtmlTemplates/) populated with
    // window.REPORT_DATA from the existing .NET data services. The report's
    // JavaScript is inlined so the page is fully self-contained.
    public async Task<IActionResult> HtmlReport(string report, string? question, string? spec, string? fromDate, string? toDate, string? minAge, string? maxAge)
    {
        // Read the query spec from the query-string parameter (Base64-encoded).
        var querySpec = DecodeQuerySpec(spec);
        var hasBrainQuery = querySpec != null && querySpec.Filters.Count > 0;

        string key;
        object rows;
        string table = "Patients";
        object parameters = new { };

        switch (report)
        {
            case "patient":
                key = "patient";
                rows = hasBrainQuery
                    ? await _queryService.QueryPatientsAsync(querySpec!)
                    : await _dataService.GetPatientReportAsync();
                break;
            case "transplant":
                key = "transplant_event";
                rows = hasBrainQuery
                    ? await _queryService.QueryTransplantEventsAsync(querySpec!)
                    : await _dataService.GetTransplantEventReportAsync();
                table = "TransplantEvents";
                break;
            case "clinical":
                key = "patient_clinical_summary";
                var from = DateTime.TryParse(fromDate, out var f) ? f : new DateTime(2026, 1, 1);
                var to = DateTime.TryParse(toDate, out var t) ? t : new DateTime(2026, 12, 31);
                var minA = int.TryParse(minAge, out var mn) ? mn : 18;
                var maxA = int.TryParse(maxAge, out var mx) ? mx : 70;
                var clinicalRows = await _dataService.GetClinicalFlatRowsAsync(from, to, minA, maxA, "All");
                // Apply brain-decoded filters (e.g. gender, facility) — this
                // report is built from denormalized rows, so filtering happens
                // in memory rather than through QueryPatients/TransplantEvents.
                if (hasBrainQuery)
                    clinicalRows = _queryService.FilterClinicalRows(clinicalRows, querySpec!);
                rows = clinicalRows;
                parameters = new
                {
                    fromDate = from.ToString("yyyy-MM-dd"),
                    toDate = to.ToString("yyyy-MM-dd"),
                    minAge = minA,
                    maxAge = maxA,
                };
                break;
            default:
                return RedirectToAction(nameof(HtmlReports));
        }

        // Fail closed: if any brain-decoded filter was skipped (blocked PHI
        // field, disallowed operator, or no navigation path), do NOT render a
        // broader result than the user asked for. Probing a blocked field
        // (e.g. "MRN-00003") must not dump the whole table.
        var skippedFilters = hasBrainQuery
            ? querySpec!.Filters.Where(f => f.Status == "skipped").ToList()
            : new List<QueryFilter>();
        if (skippedFilters.Count > 0)
        {
            _logger.LogWarning(
                "Report '{Report}' not populated: {Count} filter(s) skipped ({Fields})",
                report, skippedFilters.Count,
                string.Join(", ", skippedFilters.Select(f => $"{f.Table}.{f.Field}")));
            rows = Array.Empty<object>();
        }

        var rowList = (System.Collections.ICollection)rows;
        var narrative = "";
        object? chart = null;

        if (skippedFilters.Count > 0)
        {
            narrative = "Your question included a condition that cannot be used for "
                + "filtering (a protected or unsupported field: "
                + string.Join(", ", skippedFilters.Select(f => f.Field).Distinct())
                + "). To avoid showing more data than you asked for, no rows are "
                + "displayed. Please rephrase using supported filters (e.g. name, "
                + "gender, facility, dates).";
        }
        else if (!string.IsNullOrWhiteSpace(question))
        {
            try
            {
                var summary = await _brainClient.SummarizeAsync(question, rows, rowList.Count, table);
                narrative = summary.Summary;
                if (summary.Chart.HasValue && summary.Chart.Value.ValueKind != JsonValueKind.Null)
                    chart = summary.Chart;
            }
            catch (Exception ex)
            {
                _logger.LogWarning(ex, "Brain /summarize failed, proceeding without narrative");
            }
        }

        var reportData = new
        {
            parameters,
            rows,
            narrative,
            chart,
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

        html = html.Replace("<!-- REPORT_DATA -->", $"<script>window.REPORT_DATA = {json};</script>");
        html = html.Replace($"<script src=\"{key}.js\" defer></script>", $"<script>{js}</script>");

        html = html.Replace("</body>", @"<script src=""/lib/chartjs/chart.umd.min.js""></script>
<script>
document.addEventListener('DOMContentLoaded', function() {
  var d = window.REPORT_DATA;
  if (!d || !d.chart || !d.chart.type) return;
  var anchor = document.querySelector('[data-narrative]') || document.querySelector('.report__footer');
  if (!anchor) return;
  var wrap = document.createElement('section');
  wrap.style.cssText = 'max-width:600px;margin:1.5rem auto;';
  var canvas = document.createElement('canvas');
  wrap.appendChild(canvas);
  anchor.parentNode.insertBefore(wrap, anchor.nextSibling);
  new Chart(canvas, {
    type: d.chart.type,
    data: {
      labels: d.chart.labels || [],
      datasets: [{ label: d.chart.title || '', data: d.chart.values || [],
        backgroundColor: ['#4e79a7','#f28e2b','#e15759','#76b7b2','#59a14f','#edc948','#b07aa1','#ff9da7','#9c755f','#bab0ac'] }]
    },
    options: { responsive: true, plugins: { legend: { display: d.chart.type === 'pie' } } }
  });
});
</script>
</body>");

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
    public async Task<IActionResult> RdlView(string report, string? fromDate, string? toDate, string? minAge, string? maxAge)
    {
      try
      {
        byte[] pdf;
        switch (report)
        {
            case "patient":
                pdf = await _rdlRenderClient.RenderAsync("patient", await _dataService.GetPatientReportAsync());
                break;
            case "transplant":
                var transplantParameters = new Dictionary<string, string>
                {
                    ["FromDate"] = fromDate ?? "2026-01-01",
                    ["ToDate"] = toDate ?? "2026-12-31",
                };
                pdf = await _rdlRenderClient.RenderAsync("transplant", await _dataService.GetTransplantEventReportAsync(), transplantParameters);
                break;
            case "clinical":
                // Resolve the filters (blank -> sensible defaults), filter the data in
                // .NET (the RDL is rendered with fed data, so its SQL WHERE never runs),
                // and echo the same filters into the report via its parameters.
                var from = DateTime.TryParse(fromDate, out var f) ? f : new DateTime(2026, 1, 1);
                var to = DateTime.TryParse(toDate, out var t) ? t : new DateTime(2026, 12, 31);
                var minA = int.TryParse(minAge, out var mn) ? mn : 18;
                var maxA = int.TryParse(maxAge, out var mx) ? mx : 70;

                var rows = await _dataService.GetClinicalFlatRowsAsync(from, to, minA, maxA, "All");
                var parameters = new Dictionary<string, string>
                {
                    ["FromDate"] = from.ToString("yyyy-MM-dd"),
                    ["ToDate"] = to.ToString("yyyy-MM-dd"),
                    ["Status"] = "All",
                    ["MinAge"] = minA.ToString(),
                    ["MaxAge"] = maxA.ToString(),
                    ["rptUser"] = User?.Identity?.Name ?? "system",
                };
                pdf = await _rdlRenderClient.RenderAsync("clinical", rows, parameters);
                break;
            default:
                return NotFound();
        }

        return File(pdf, "application/pdf");
      }
      catch (Exception ex)
      {
        _logger.LogError(ex, "RDL render failed for report {Report}", report);
        var svc = _config["RdlRenderService:BaseUrl"] ?? "http://localhost:5250/";
        var detail = System.Net.WebUtility.HtmlEncode(ex.Message);
        var msg = $@"<!doctype html><html><head><meta charset=""utf-8""></head>
<body style=""font-family:'Segoe UI',Arial,sans-serif;padding:24px;color:#333;line-height:1.5"">
  <h3 style=""color:#b02a37;margin:0 0 .5rem"">SSRS report could not be rendered</h3>
  <p>The RDL rendering service didn't respond. The <b>RdlRenderService</b> (.NET Framework 4.8)
     must be running for the SSRS / PDF report path.</p>
  <p><b>Start it:</b> <code>dotnet run --project DotNetApp/RdlRenderService</code>
     &nbsp;(expected at <code>{svc}</code>)</p>
  <p style=""color:#999;font-size:.85rem"">Detail: {detail}</p>
</body></html>";
        return Content(msg, "text/html");
      }
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
