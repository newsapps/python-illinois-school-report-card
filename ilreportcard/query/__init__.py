from sqlalchemy.sql import text

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
        (CAST(ps.absent_ela + ps.refusal_ela AS float) / ps.tested_enrollment_ela) * 100 AS pct_not_tested_ela,
        ps.tested_enrollment_math,
        ps.tested_math,
        (CAST(ps.absent_math + ps.refusal_math AS float) / ps.tested_enrollment_math) * 100 AS pct_not_tested_math,
        pd.tested_enrollment_ela AS tested_enrollment_ela_district,
        pd.tested_ela AS tested_ela_district,
        (CAST(pd.absent_ela + pd.refusal_ela AS float) / pd.tested_enrollment_ela) * 100 AS pct_not_tested_ela_district,
        pd.tested_enrollment_math AS tested_enrollment_math_district,
        pd.tested_math AS tested_math_district,
        (CAST(pd.absent_math + pd.refusal_math AS float) / pd.tested_enrollment_math) * 100 AS pct_not_tested_math_district
    FROM assessment_2015_schools s 
    JOIN parcc_participation_2015 ps on ps.rcdts = s.school_id
    JOIN parcc_participation_2015 pd on pd.rcdts = overlay(s.school_id placing
    '0000' from 12 for 4)
    JOIN assessment_2015_overall_achievement_parcc_dlm_performance a ON a.school_id = s.school_id
    """

    if rcdts_ids is not None:
        query += "WHERE s.school_id = ANY(:rcdts_ids)"

    s = text(query)
    results = []
    for row in conn.execute(s, rcdts_ids=rcdts_ids):
        row_dict = {k:v for k,v in row.items()}
        results.append(row_dict)

    return results
