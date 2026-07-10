using Microsoft.AspNetCore.Mvc;
using PatientReports.DataServices;
using PatientReports.Models;

namespace PatientReports.Controllers;

public class ReportsController : Controller
{
    private readonly PatientDataService _dataService;
    private readonly PdfReportService _pdfService;

    public ReportsController(PatientDataService dataService, PdfReportService pdfService)
    {
        _dataService = dataService;
        _pdfService = pdfService;
    }

    // Unified reports hub: a report dropdown + a single "Generate Report" button.
    // The selected report is rendered below the selector.
    public async Task<IActionResult> Index(string? report)
    {
        var vm = new ReportsHubViewModel { SelectedReport = report };

        switch (report)
        {
            case "patient":
                vm.PatientRows = await _dataService.GetPatientReportAsync();
                break;
            case "transplant":
                vm.TransplantRows = await _dataService.GetTransplantEventReportAsync();
                break;
            case "clinical":
                vm.Clinical = await _dataService.GetClinicalSummaryAsync();
                break;
        }

        return View(vm);
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
