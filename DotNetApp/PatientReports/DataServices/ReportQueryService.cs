using System.Linq.Expressions;
using System.Reflection;
using Microsoft.EntityFrameworkCore;
using PatientReports.Data;
using PatientReports.Models;

namespace PatientReports.DataServices;

public class ReportQueryService
{
    private readonly ApplicationDbContext _context;
    private readonly ILogger<ReportQueryService> _logger;

    private static readonly HashSet<string> AllowedOperators = new(StringComparer.OrdinalIgnoreCase)
    {
        "equals", "notEquals", "contains",
        "greaterThan", "greaterThanOrEqual",
        "lessThan", "lessThanOrEqual"
    };

    private static readonly Dictionary<string, Dictionary<string, string>> NavPropertyMap = new()
    {
        ["Patients"] = new() { ["Facilities"] = "Facility" },
        ["TransplantEvents"] = new() { ["Patients"] = "Patient", ["Providers"] = "Provider" },
        ["Providers"] = new() { ["Facilities"] = "Facility" },
        ["Diagnoses"] = new() { ["Patients"] = "Patient" },
        ["Medications"] = new() { ["Patients"] = "Patient" },
        ["LabResults"] = new() { ["TransplantEvents"] = "TransplantEvent" },
    };

    // 2-hop navigation: primary table → target table → [nav1, nav2]
    // e.g. TransplantEvents → Facilities goes through Patient.Facility
    private static readonly Dictionary<string, Dictionary<string, string[]>> ChainedNavMap = new()
    {
        ["TransplantEvents"] = new() { ["Facilities"] = new[] { "Patient", "Facility" } },
        ["LabResults"] = new() { ["Patients"] = new[] { "TransplantEvent", "Patient" } },
        ["Diagnoses"] = new() { ["Facilities"] = new[] { "Patient", "Facility" } },
        ["Medications"] = new() { ["Facilities"] = new[] { "Patient", "Facility" } },
    };

    // Per-table allowlist of fields a brain-generated (or user-supplied) spec
    // may filter on. Reflection-based predicate building would otherwise allow
    // probing any entity property — including PHI contact fields — via
    // contains/range filters. Keys and values are case-insensitive.
    private static readonly Dictionary<string, HashSet<string>> FilterableFields = new(StringComparer.OrdinalIgnoreCase)
    {
        ["Patients"] = new(StringComparer.OrdinalIgnoreCase)
            { "FirstName", "LastName", "Gender", "DateOfBirth", "Status", "HeightCm", "WeightKg" },
        ["Facilities"] = new(StringComparer.OrdinalIgnoreCase)
            { "Name", "City", "State", "FacilityType", "IsActive" },
        ["TransplantEvents"] = new(StringComparer.OrdinalIgnoreCase)
            { "DateOfVisit", "DateOfPreviousVisit", "TransplantDate", "InfusionDate",
              "DischargeDate", "EventId", "TransplantNumber", "IsInpatient", "DonorType" },
        ["Providers"] = new(StringComparer.OrdinalIgnoreCase)
            { "FirstName", "LastName", "Specialty" },
        ["Diagnoses"] = new(StringComparer.OrdinalIgnoreCase)
            { "IcdCode", "Description", "Severity", "DiagnosedDate" },
        ["Medications"] = new(StringComparer.OrdinalIgnoreCase)
            { "Name", "Dosage", "Frequency", "StartDate", "EndDate", "IsActive" },
        ["LabResults"] = new(StringComparer.OrdinalIgnoreCase)
            { "TestName", "Value", "Unit", "TakenDate" },
    };

    private static bool IsFilterableField(string table, string field)
    {
        return FilterableFields.TryGetValue(table, out var fields) && fields.Contains(field);
    }

    // The clinical summary report is built from denormalized ClinicalFlatRow
    // objects, so brain filters (table-qualified) are applied in memory by
    // mapping each Table.Field onto the corresponding flat-row property.
    // This map is also the allowlist for the clinical report.
    private static readonly Dictionary<string, string> ClinicalFieldMap = new(StringComparer.OrdinalIgnoreCase)
    {
        ["Patients.Gender"] = nameof(ClinicalFlatRow.Gender),
        ["Patients.Status"] = nameof(ClinicalFlatRow.Status),
        ["Patients.DateOfBirth"] = nameof(ClinicalFlatRow.DateOfBirth),
        ["Patients.FirstName"] = nameof(ClinicalFlatRow.PatientName),
        ["Patients.LastName"] = nameof(ClinicalFlatRow.PatientName),
        ["Facilities.Name"] = nameof(ClinicalFlatRow.FacilityName),
        ["Facilities.City"] = nameof(ClinicalFlatRow.FacilityCity),
        ["Facilities.State"] = nameof(ClinicalFlatRow.FacilityState),
        ["TransplantEvents.DateOfVisit"] = nameof(ClinicalFlatRow.DateOfVisit),
        ["TransplantEvents.DateOfPreviousVisit"] = nameof(ClinicalFlatRow.DateOfPreviousVisit),
        ["TransplantEvents.DonorType"] = nameof(ClinicalFlatRow.DonorType),
        ["TransplantEvents.IsInpatient"] = nameof(ClinicalFlatRow.IsInpatient),
        ["TransplantEvents.EventId"] = nameof(ClinicalFlatRow.EventId),
        ["Providers.FirstName"] = nameof(ClinicalFlatRow.ProviderName),
        ["Providers.LastName"] = nameof(ClinicalFlatRow.ProviderName),
        ["Providers.Specialty"] = nameof(ClinicalFlatRow.Specialty),
        ["LabResults.TestName"] = nameof(ClinicalFlatRow.LabTestName),
        ["LabResults.Value"] = nameof(ClinicalFlatRow.LabValue),
    };

    // Combined-name columns: a FirstName/LastName equals-filter must match as
    // a substring of "First Last" rather than the whole string.
    private static readonly HashSet<string> CombinedNameProps = new(StringComparer.OrdinalIgnoreCase)
    {
        nameof(ClinicalFlatRow.PatientName), nameof(ClinicalFlatRow.ProviderName)
    };

    /// <summary>
    /// Applies brain-decoded filters to the denormalized clinical rows in memory.
    /// Unknown or unsupported filters are marked skipped and ignored (AND-only).
    /// </summary>
    public List<ClinicalFlatRow> FilterClinicalRows(List<ClinicalFlatRow> rows, QuerySpec spec)
    {
        if (spec.Filters.Count == 0)
            return rows;

        IEnumerable<ClinicalFlatRow> result = rows;

        foreach (var filter in spec.Filters)
        {
            if (!AllowedOperators.Contains(filter.Operator))
            {
                filter.Status = "skipped";
                _logger.LogWarning("Clinical filter skipped: disallowed operator '{Op}'", filter.Operator);
                continue;
            }

            if (!ClinicalFieldMap.TryGetValue($"{filter.Table}.{filter.Field}", out var prop))
            {
                filter.Status = "skipped";
                _logger.LogWarning("Clinical filter skipped: no mapping for {Table}.{Field}",
                    filter.Table, filter.Field);
                continue;
            }

            var op = filter.Operator;
            // First/last name filters target a combined "First Last" column;
            // degrade equals to a case-insensitive substring match.
            if (CombinedNameProps.Contains(prop) && op.Equals("equals", StringComparison.OrdinalIgnoreCase))
                op = "contains";

            var predicate = BuildPredicate<ClinicalFlatRow>(typeof(ClinicalFlatRow), prop, op, filter.Value);
            if (predicate == null)
            {
                filter.Status = "skipped";
                _logger.LogWarning("Clinical filter skipped: could not build predicate for {Prop} {Op}",
                    prop, filter.Operator);
                continue;
            }

            result = result.Where(predicate.Compile());
            filter.Status = "applied";
        }

        return result.ToList();
    }

    // Operators that are not meaningful for string comparisons. If the brain
    // emits greaterThan/lessThan for a string field, the filter is skipped
    // rather than silently degraded to equals.
    private static readonly HashSet<string> NumericOnlyOperators = new(StringComparer.OrdinalIgnoreCase)
    {
        "greaterThan", "greaterThanOrEqual", "lessThan", "lessThanOrEqual"
    };

    public ReportQueryService(ApplicationDbContext context, ILogger<ReportQueryService> logger)
    {
        _context = context;
        _logger = logger;
    }

    public async Task<List<PatientReportViewModel>> QueryPatientsAsync(QuerySpec spec)
    {
        var query = _context.Patients.AsNoTracking().Include(p => p.Facility);
        var filtered = ApplyFilters(query, spec, "Patients");

        return await filtered
            .Select(p => new PatientReportViewModel
            {
                FirstName = p.FirstName,
                LastName = p.LastName,
                Gender = p.Gender,
                DateOfBirth = p.DateOfBirth,
                ContactNumber = p.ContactNumber,
                Email = p.Email,
                PhoneNumber = p.PhoneNumber
            })
            .OrderBy(p => p.LastName)
            .ToListAsync();
    }

    public async Task<List<TransplantEventReportViewModel>> QueryTransplantEventsAsync(QuerySpec spec)
    {
        var query = _context.TransplantEvents.AsNoTracking()
            .Include(e => e.Patient).ThenInclude(p => p.Facility)
            .Include(e => e.Provider);
        var filtered = ApplyFilters(query, spec, "TransplantEvents");

        return await filtered
            .Select(e => new TransplantEventReportViewModel
            {
                PatientName = e.Patient.FirstName + " " + e.Patient.LastName,
                DateOfVisit = e.DateOfVisit,
                DateOfPreviousVisit = e.DateOfPreviousVisit,
                TransplantDate = e.TransplantDate,
                InfusionDate = e.InfusionDate,
                EventId = e.EventId,
                TransplantNumber = e.TransplantNumber,
                DonorType = e.DonorType,
                IsInpatient = e.IsInpatient ? "Yes" : "No"
            })
            .OrderBy(e => e.DateOfVisit)
            .ToListAsync();
    }

    private IQueryable<T> ApplyFilters<T>(IQueryable<T> query, QuerySpec spec, string primaryTable) where T : class
    {
        if (spec.Filters.Count == 0)
            return query;

        var entityType = typeof(T);

        foreach (var filter in spec.Filters)
        {
            if (!AllowedOperators.Contains(filter.Operator))
            {
                filter.Status = "skipped";
                _logger.LogWarning("Skipping filter: disallowed operator '{Op}'", filter.Operator);
                continue;
            }

            if (!IsFilterableField(filter.Table, filter.Field))
            {
                filter.Status = "skipped";
                _logger.LogWarning("Skipping filter: field {Table}.{Field} is not filterable",
                    filter.Table, filter.Field);
                continue;
            }

            try
            {
                if (string.Equals(filter.Table, primaryTable, StringComparison.OrdinalIgnoreCase))
                {
                    var predicate = BuildPredicate<T>(entityType, filter.Field, filter.Operator, filter.Value);
                    if (predicate != null)
                    {
                        query = query.Where(predicate);
                        filter.Status = "applied";
                    }
                    else
                    {
                        filter.Status = "skipped";
                        _logger.LogWarning("Could not build predicate for {Table}.{Field} {Op}",
                            filter.Table, filter.Field, filter.Operator);
                    }
                }
                else
                {
                    var navProp = ResolveNavProperty(primaryTable, filter.Table);
                    if (navProp != null)
                    {
                        var predicate = BuildNavPredicate<T>(entityType, navProp, filter.Field, filter.Operator, filter.Value);
                        if (predicate != null)
                        {
                            query = query.Where(predicate);
                            filter.Status = "applied";
                        }
                        else
                        {
                            filter.Status = "skipped";
                            _logger.LogWarning("Could not build nav predicate for {Nav}.{Field} {Op}",
                                navProp, filter.Field, filter.Operator);
                        }
                    }
                    else
                    {
                        var chain = ResolveChainedNav(primaryTable, filter.Table);
                        if (chain != null)
                        {
                            var predicate = BuildChainedNavPredicate<T>(entityType, chain, filter.Field, filter.Operator, filter.Value);
                            if (predicate != null)
                            {
                                query = query.Where(predicate);
                                filter.Status = "applied";
                            }
                            else
                            {
                                filter.Status = "skipped";
                                _logger.LogWarning("Could not build chained nav predicate for {Chain}.{Field} {Op}",
                                    string.Join(".", chain), filter.Field, filter.Operator);
                            }
                        }
                        else
                        {
                            filter.Status = "skipped";
                            _logger.LogWarning("No navigation from {Primary} to {Target}", primaryTable, filter.Table);
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                filter.Status = "skipped";
                _logger.LogWarning(ex, "Failed to apply filter {Table}.{Field} {Op} {Value}",
                    filter.Table, filter.Field, filter.Operator, LogSafe(filter.Field, filter.Value));
            }
        }

        return query;
    }

    private static string? ResolveNavProperty(string primaryTable, string targetTable)
    {
        if (NavPropertyMap.TryGetValue(primaryTable, out var navs) &&
            navs.TryGetValue(targetTable, out var navProp))
            return navProp;
        return null;
    }

    private static string[]? ResolveChainedNav(string primaryTable, string targetTable)
    {
        if (ChainedNavMap.TryGetValue(primaryTable, out var chains) &&
            chains.TryGetValue(targetTable, out var chain))
            return chain;
        return null;
    }

    private static Expression<Func<T, bool>>? BuildPredicate<T>(
        Type entityType, string fieldName, string op, string value)
    {
        var property = entityType.GetProperty(fieldName,
            BindingFlags.Public | BindingFlags.Instance | BindingFlags.IgnoreCase);
        if (property == null) return null;

        var param = Expression.Parameter(typeof(T), "x");
        var member = Expression.Property(param, property);
        return BuildComparison<T>(param, member, property.PropertyType, op, value);
    }

    private static Expression<Func<T, bool>>? BuildChainedNavPredicate<T>(
        Type entityType, string[] chain, string fieldName, string op, string value)
    {
        var param = Expression.Parameter(typeof(T), "x");
        Expression current = param;
        var currentType = entityType;

        foreach (var navName in chain)
        {
            var prop = currentType.GetProperty(navName,
                BindingFlags.Public | BindingFlags.Instance | BindingFlags.IgnoreCase);
            if (prop == null) return null;
            current = Expression.Property(current, prop);
            currentType = prop.PropertyType;
        }

        var targetProp = currentType.GetProperty(fieldName,
            BindingFlags.Public | BindingFlags.Instance | BindingFlags.IgnoreCase);
        if (targetProp == null) return null;

        var member = Expression.Property(current, targetProp);
        return BuildComparison<T>(param, member, targetProp.PropertyType, op, value);
    }

    private static Expression<Func<T, bool>>? BuildNavPredicate<T>(
        Type entityType, string navPropertyName, string fieldName, string op, string value)
    {
        var navProp = entityType.GetProperty(navPropertyName,
            BindingFlags.Public | BindingFlags.Instance | BindingFlags.IgnoreCase);
        if (navProp == null) return null;

        var targetProp = navProp.PropertyType.GetProperty(fieldName,
            BindingFlags.Public | BindingFlags.Instance | BindingFlags.IgnoreCase);
        if (targetProp == null) return null;

        var param = Expression.Parameter(typeof(T), "x");
        var navAccess = Expression.Property(param, navProp);
        var member = Expression.Property(navAccess, targetProp);
        return BuildComparison<T>(param, member, targetProp.PropertyType, op, value);
    }

    private static Expression<Func<T, bool>>? BuildComparison<T>(
        ParameterExpression param, MemberExpression member, Type propertyType, string op, string value)
    {
        var underlying = Nullable.GetUnderlyingType(propertyType) ?? propertyType;

        if (underlying == typeof(string))
        {
            // Reject numeric-only operators on string fields rather than
            // silently falling through to equals.
            if (NumericOnlyOperators.Contains(op))
                return null;

            // Null-safe: coalesce null strings to empty string before calling
            // ToLower(), preventing NullReferenceException on nullable columns.
            var emptyString = Expression.Constant(string.Empty);
            var coalesced = Expression.Coalesce(member, emptyString);
            var lowerMember = Expression.Call(coalesced, typeof(string).GetMethod("ToLower", Type.EmptyTypes)!);
            var lowerValue = Expression.Constant(value.ToLower());

            Expression body = op.ToLower() switch
            {
                "contains" => Expression.Call(lowerMember,
                    typeof(string).GetMethod("Contains", new[] { typeof(string) })!, lowerValue),
                "notequals" => Expression.NotEqual(lowerMember, lowerValue),
                _ => Expression.Equal(lowerMember, lowerValue),
            };
            return Expression.Lambda<Func<T, bool>>(body, param);
        }

        if (underlying == typeof(bool))
        {
            var boolVal = value.Equals("true", StringComparison.OrdinalIgnoreCase)
                          || value.Equals("yes", StringComparison.OrdinalIgnoreCase);
            var constant = Expression.Constant(boolVal, propertyType);
            var body = op.Equals("notEquals", StringComparison.OrdinalIgnoreCase)
                ? (Expression)Expression.NotEqual(member, constant)
                : Expression.Equal(member, constant);
            return Expression.Lambda<Func<T, bool>>(body, param);
        }

        object? parsedValue = null;
        if (underlying == typeof(DateTime) && DateTime.TryParse(value, out var dt)) parsedValue = dt;
        else if (underlying == typeof(int) && int.TryParse(value, out var i)) parsedValue = i;
        else if (underlying == typeof(double) && double.TryParse(value, out var d)) parsedValue = d;

        if (parsedValue == null) return null;

        Expression left = member;
        if (propertyType != underlying)
            left = Expression.Convert(member, underlying);

        var constant2 = Expression.Constant(parsedValue, underlying);

        Expression comparison = op.ToLower() switch
        {
            "greaterthan" => Expression.GreaterThan(left, constant2),
            "greaterthanorequal" => Expression.GreaterThanOrEqual(left, constant2),
            "lessthan" => Expression.LessThan(left, constant2),
            "lessthanorequal" => Expression.LessThanOrEqual(left, constant2),
            "notequals" => Expression.NotEqual(left, constant2),
            _ => Expression.Equal(left, constant2),
        };

        return Expression.Lambda<Func<T, bool>>(comparison, param);
    }

    private static string LogSafe(string field, string value)
    {
        var phiFields = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
        {
            "FirstName", "LastName", "MRN", "ContactNumber", "Email", "PhoneNumber", "DateOfBirth"
        };
        return phiFields.Contains(field) ? "[FILTERED]" : value;
    }
}
