using Microsoft.AspNetCore.Mvc;
using PatientReports.DataServices;

namespace PatientReports.Controllers;

public class ReportsController : Controller
{
    private readonly PatientDataService _dataService;

    public ReportsController(PatientDataService dataService)
    {
        _dataService = dataService;
    }

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
