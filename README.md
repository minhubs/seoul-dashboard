# seoul-dashboard

https://aistudio.google.com/app/prompts?state=%7B%22ids%22:%5B%221dqI2rx4I1tI3FFLRyS0gOkD1F3AteT22%22%5D,%22action%22:%22open%22,%22userId%22:%22118053103000971677520%22,%22resourceKeys%22:%7B%7D%7D&usp=sharing


사용한 데이터
- 서울시 문화공간 정보
- 서울시 관광 명소
- 서울시 문화행사 정보
총 3개의 공공데이터를 활용하여 데이터베이스를 구성하였다.

1. 자치구별 문화시설 수
SQL: SELECT 자치구, COUNT(*) AS 시설수
FROM culture_space
GROUP BY 자치구
ORDER BY 시설수 DESC

인사이트:
- 서울시 문화시설은 특정 자치구(강남, 종로, 중구 등)에 집중되어 있다.
- 이는 지역 간 문화 인프라 격차를 의미하며 균형 있는 정책이 필요하다.

2. 문화공간 유형 분포
SQL: SELECT 유형, COUNT(*) AS 개수
FROM culture_space
GROUP BY 유형

인사이트:
- 도서관, 박물관 등 특정 유형의 시설이 높은 비중을 차지한다.
- 문화 다양성 측면에서 편중 현상이 나타난다.

3. 무료 vs 유료 문화시설 비율
SQL: SELECT 무료구분, COUNT(*) AS 개수
FROM culture_space
GROUP BY 무료구분

인사이트:
- 무료 시설 비율은 시민의 문화 접근성을 나타내는 핵심 지표이다.
- 유료 시설 비중이 높을 경우 문화 접근성이 낮아질 수 있다.

4. 결론
- 서울시 문화 인프라는 지역별로 불균형하게 분포되어 있음
- 무료 시설은 문화 접근성 향상에 중요한 역할 수행
- 다양한 문화시설 유형 확대 필요 
