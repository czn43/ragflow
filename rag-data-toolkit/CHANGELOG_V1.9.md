# v1.9 Guangdong Education & Talent Competition Pack

## Added
- `config/tasks/guangdong_education_talent_p0.yaml`
- Guangdong Education Department policy / explanation source configs
- Guangdong Education Examinations Authority Gaokao / high-school exam source configs
- Guangdong HRSS employment / skilled-talent source configs
- Direct seed configs for 2026 government work report, Talent Youyue Card, graduate employment policy, student-aid policy
- `benchmarks/Guangdong_Education_Talent_100Q.xlsx`
- `README_COMPETITION_GD_EDU_TALENT.md`
- `run_guangdong_p0.bat`

## Strategy
First ingest high-information-density official sources, validate RAW/CLEAN/FINAL, then use the 100-question benchmark to identify missing knowledge blocks before expanding crawl volume.
