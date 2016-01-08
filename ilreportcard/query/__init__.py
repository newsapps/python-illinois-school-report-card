from sqlalchemy.sql import text

CHICAGO_AREA_COUNTIES = [
    'Cook',
    'Dupage',
    'Will',
    'Lake',
    'McHenry',
    'Kane',
]

def summary_query(conn, year, rcdts_ids=None):
    f = globals()['summary_query_{}'.format(year)]
    return f(conn, rcdts_ids)


def summary_query_2015(conn, rcdts_ids=None):
    """
    Query for print agate

    This includes:

    * School RCDTS ID
    * School Name
    * District RCDTS ID
    * District Name
    * Grades in School
    * % proficient PARCC ELA School (Column 259)
    * % proficient PARCC ELA District (Column 260)
    * % proficient PARCC Math School (Column 263)
    * % proficient PARCC Math District (Column 265)
    * Tested enrollment PARCC ELA School
    * # Tested PARCC ELA School
    * Tested enrollment PARCC Math School
    * # Tested PARCC Math School
    * Tested enrollment PARCC ELA District
    * # Tested PARCC ELA District
    * Tested enrollment PARCC Math District
    * # Tested PARCC Math District
    
    """
    # TODO: Document this and where the join table is coming from 
    query = """
    SELECT s.school_id,
        s.school_name,
        overlay(s.school_id placing '0000' from 12 for 4) AS district_id,
        s.district_name,
        s.grades_in_school,
        a.school_pct_proficiency_in_ela_parcc_2015_ela,
        a.district_pct_proficiency_in_ela_parcc_2015_ela,
        a.school_pct_proficiency_in_math_parcc_2015_math,
        a.district_pct_proficiency_in_math_parcc_2015_math,
        ps.tested_enrollment_ela,
        (CAST(coalesce(ps.absent_ela, 0) + coalesce(ps.refusal_ela, 0) AS float) / ps.tested_enrollment_ela) * 100 AS pct_not_tested_ela,
        ps.tested_enrollment_math,
        ps.tested_math,
        (CAST(coalesce(ps.absent_math, 0) + coalesce(ps.refusal_math, 0) AS float) / ps.tested_enrollment_math) * 100 AS pct_not_tested_math,
        pd.tested_enrollment_ela AS tested_enrollment_ela_district,
        pd.tested_ela AS tested_ela_district,
        (CAST(coalesce(pd.absent_ela, 0) + coalesce(pd.refusal_ela, 0) AS float) / pd.tested_enrollment_ela) * 100 AS pct_not_tested_ela_district,
        pd.tested_enrollment_math AS tested_enrollment_math_district,
        pd.tested_math AS tested_math_district,
        (CAST(coalesce(pd.absent_math, 0) + coalesce(pd.refusal_math, 0) AS float) / pd.tested_enrollment_math) * 100 AS pct_not_tested_math_district
    FROM assessment_2015_schools s 
    JOIN parcc_participation_2015 ps on ps.rcdts = s.school_id
    JOIN parcc_participation_2015 pd on pd.rcdts = overlay(s.school_id placing
    '0000' from 12 for 4)
    JOIN assessment_2015_overall_achievement_parcc_dlm_performance a ON a.school_id = s.school_id
    """

    if rcdts_ids is not None:
        query += "WHERE s.school_id = ANY(:rcdts_ids)"

    s = text(query)
    return get_result_dicts(conn.execute(s, rcdts_ids=rcdts_ids))


def best_worst_performers_query(conn, year, subject, order, limit=50, counties=None):
    f = globals()['best_worst_performers_query_{}'.format(year)]
    return f(conn, subject, order, limit, counties)


def best_worst_performers_query_2015(conn, subject, order, limit, counties):
    """
    Query to get best and worst peformers by subject specified

    Query to find top performers in ELA with participation rates in the Chicago area
    and that had at least 85% participation among eligible students
    
    This includes:
    
    * School RDTS
    * School county
    * District/school number
    * District name
    * City
    * % proficient
    * Tested students
    * Enrollment
    * % tested

    """

    query_params = {}

    query = """
    SELECT ps.rcdts as school_id,
      ps.district_name_school_name,
      ps.city,
      ps.county,
      ps.district_number,
      ps.tested_enrollment_{subject},
      ps.tested_{subject},
      CAST(tested_{subject} as float)/tested_enrollment_{subject} as percent_tested_{subject},
      pd.school_pct_proficiency_in_{subject}_parcc_2015_{subject} as passing
    FROM parcc_participation_2015 ps 
    JOIN assessment_2015_overall_achievement_parcc_dlm_performance pd on pd.school_id = ps.rcdts
    WHERE (CAST(ps.tested_{subject} as float)/ps.tested_enrollment_{subject}) >= .85
    """.format(subject=subject)

    if counties is not None:
        query += 'AND ps.county = ANY(:counties)'
        query_params['counties'] = counties

    query += """
    ORDER BY passing {order}
    LIMIT {limit};
    """.format(order=order, limit=limit)

    s = text(query)

    return get_result_dicts(conn.execute(s, **query_params))


def get_result_dicts(result):
    results = []
    for row in result:
        row_dict = {k:v for k,v in row.items()}
        results.append(row_dict)

    return results