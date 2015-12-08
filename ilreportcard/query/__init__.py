from sqlalchemy.sql import text

def summary_query(conn, year, school_ids=None):
    f = globals()['summary_query_{}'.format(year)]
    return f(conn, school_ids)


def summary_query_2015(conn, school_ids=None):
    """
    Query for print agate

    This includes:

    * % passing PARCC ELA School (Column 259)
    * % passing PARCC ELA District (Column 260)
    * % passing PARCC Math School (Column 263)
    * % passing PARCC Math District (Column 265)
    * Total enrollment ELA School (Column 7)
    * Total enrollment ELA District (Column 9)
    * % not taking ELA tests School (Column 11)
    * % not taking ELA tests District (Column 13)
    * Total enrollment Math School (Column 123)
    * Total enrollment Math District (Column 125)
    * % not taking Math School (Column 127) 
    * % not taking Math District (Column 129)
    
    """
    query = """
    SELECT s.school_id, s.school_type_code, s.school_name, s.district_name,
        s.grades_in_school,
        a.school_pct_proficiency_in_ela_parcc_2015_ela,
        a.district_pct_proficiency_in_ela_parcc_2015_ela,
        a.school_pct_proficiency_in_math_parcc_2015_math,
        a.district_pct_proficiency_in_math_parcc_2015_math,
        p.total_school_enrollment_in_ela_grade_3_8_hs_all,
        p.total_district_enrollment_in_ela_grade_3_8_hs_all,
        p.pct_not_taking_ela_tests_school_all,
        p.pct_not_taking_ela_tests_district_all,
        p.total_school_enrollment_in_math_grade_3_8_hs_all,
        p.total_district_enrollment_in_math_grade_3_8_hs_all,
        p.pct_not_taking_math_tests_school_all,
        p.pct_not_taking_math_tests_district_all
    FROM assessment_2015_schools s 
    JOIN assessment_2015_overall_achievement_parcc_dlm_performance a ON a.school_id = s.school_id
    JOIN assessment_2015_participation p ON p.school_id = s.school_id
    """

    if school_ids is not None:
        query += "WHERE s.school_id = ANY(:school_ids)"

    s = text(query)
    results = []
    for row in conn.execute(s, school_ids=school_ids):
        row_dict = {k:v for k,v in row.items()}
        results.append(row_dict)

    return results
