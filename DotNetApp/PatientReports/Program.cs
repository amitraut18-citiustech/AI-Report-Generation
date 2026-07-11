using Microsoft.EntityFrameworkCore;
using PatientReports.Data;
using PatientReports.DataServices;
using PdfSharp.Fonts;

// PDFsharp core build has no system-font access; supply a resolver for the PDF reports.
GlobalFontSettings.FontResolver = new WindowsFontResolver();

var builder = WebApplication.CreateBuilder(args);

// Add services to the container.
builder.Services.AddControllersWithViews();
builder.Services.AddScoped<PatientReports.DataServices.PdfReportService>();
var dbPath = Path.Combine(builder.Environment.ContentRootPath, "db", "PatientDB.db");
Directory.CreateDirectory(Path.GetDirectoryName(dbPath)!);
builder.Services.AddDbContext<ApplicationDbContext>(options =>
    options.UseSqlite($"Data Source={dbPath}"));
builder.Services.AddScoped<PatientDataService>();
builder.Services.AddHttpClient<RdlRenderClient>(client =>
{
    var baseUrl = builder.Configuration["RdlRenderService:BaseUrl"] ?? "http://localhost:5250/";
    client.BaseAddress = new Uri(baseUrl);
});

var app = builder.Build();

// Configure the HTTP request pipeline.
if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Home/Error");
    // The default HSTS value is 30 days. You may want to change this for production scenarios, see https://aka.ms/aspnetcore-hsts.
    app.UseHsts();
}

app.UseHttpsRedirection();
app.UseStaticFiles();

app.UseRouting();

app.UseAuthorization();

using (var scope = app.Services.CreateScope())
{
    var services = scope.ServiceProvider;
    await SeedData.InitializeAsync(services);
}

app.MapControllerRoute(
    name: "default",
    pattern: "{controller=Home}/{action=Index}/{id?}");

app.Run();
