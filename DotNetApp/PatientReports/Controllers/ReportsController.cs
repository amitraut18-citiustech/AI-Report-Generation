using Microsoft.AspNetCore.Mvc;
using PatientReports.DataServices;
using PatientReports.Models;

namespace PatientReports.Controllers;

public class ReportsController : Controller
{
    private readonly PatientDataService _dataService;

    public ReportsController(PatientDataService dataService)
    {
        _dataService = dataService;
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
