using System;
using System.Collections.Generic;
using System.Data;
using System.IO;
using System.Linq;
using System.Reflection;
using Microsoft.Reporting.WebForms;
using Newtonsoft.Json.Linq;

namespace RdlRenderService
{
    public static class RdlRenderer
    {
        private static readonly string ReportsDir = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "Reports");

        public static byte[] Render(string report, JArray rows, Dictionary<string, string> parameters)
        {
            switch (report)
            {
                case "patient":
                    return RenderReport("PatientReport.rdl", "dsPatient",
                        ToDataTable(rows.ToObject<List<PatientRow>>(), null), null);

                case "transplant":
                    var transplantRows = rows.ToObject<List<TransplantEventRow>>();
                    var countsByPatient = transplantRows
                        .GroupBy(r => r.PatientName)
                        .ToDictionary(g => g.Key, g => g.Count());
                    foreach (var row in transplantRows)
                    {
                        row.TotalTransplants = countsByPatient[row.PatientName];
                    }
                    return RenderReport("TransplantEventReport.rdl", "dsTransplantEvent",
                        ToDataTable(transplantRows, null), parameters);

                case "clinical":
                    var columnOverrides = new Dictionary<string, string> { { "Mrn", "MRN" } };
                    return RenderReport("PatientClinicalSummaryReport.rdl", "dsClinical",
                        ToDataTable(rows.ToObject<List<ClinicalFlatRow>>(), columnOverrides), parameters);

                default:
                    throw new ArgumentException("Unknown report: " + report);
            }
        }

        private static byte[] RenderReport(string rdlFileName, string dataSetName, DataTable table, Dictionary<string, string> parameters)
        {
            var localReport = new LocalReport();
            localReport.ReportPath = Path.Combine(ReportsDir, rdlFileName);
            localReport.DataSources.Add(new ReportDataSource(dataSetName, table));

            if (parameters != null && parameters.Count > 0)
            {
                var reportParameters = new List<ReportParameter>();
                foreach (var kvp in parameters)
                {
                    reportParameters.Add(new ReportParameter(kvp.Key, kvp.Value));
                }
                localReport.SetParameters(reportParameters);
            }

            return localReport.Render("PDF");
        }

        // Builds a DataTable whose column names/types match the RDL Fields the report
        // was authored against. columnNameOverrides remaps a C# property name (e.g.
        // "Mrn") to the RDL's DataField name (e.g. "MRN") where they differ.
        private static DataTable ToDataTable<T>(List<T> items, Dictionary<string, string> columnNameOverrides)
        {
            var table = new DataTable();
            var props = typeof(T).GetProperties(BindingFlags.Public | BindingFlags.Instance);

            foreach (var prop in props)
            {
                var columnName = prop.Name;
                if (columnNameOverrides != null && columnNameOverrides.TryGetValue(prop.Name, out var overrideName))
                {
                    columnName = overrideName;
                }
                var columnType = Nullable.GetUnderlyingType(prop.PropertyType) ?? prop.PropertyType;
                table.Columns.Add(columnName, columnType);
            }

            if (items == null)
            {
                return table;
            }

            foreach (var item in items)
            {
                var row = table.NewRow();
                foreach (var prop in props)
                {
                    var columnName = prop.Name;
                    if (columnNameOverrides != null && columnNameOverrides.TryGetValue(prop.Name, out var overrideName))
                    {
                        columnName = overrideName;
                    }
                    var value = prop.GetValue(item, null);
                    row[columnName] = value ?? DBNull.Value;
                }
                table.Rows.Add(row);
            }

            return table;
        }
    }
}
