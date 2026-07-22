# RainRoute Data Pipeline

기상청 API 기반 수치예보, 레이더 및 지상관측 자료의 수집·파싱·검증·정규화 파이프라인.

## Sources

- KIM L010
- UM L015
- Radar HSP
- Radar HSR
- AWS minute observations
- AWS objective-analysis grids
- Radar values collocated at AWS stations
- NWP and radar grid metadata

## Storage

대용량 자료는 Git 저장소 밖의 `/srv/rainroute/data`에 저장한다.
