# GridCraft 카멜케이스 수식 가이드

DB 컬럼명을 Java VO 필드명이나 MyBatis 프로퍼티명으로 변환하는 예제입니다.
GridCraft v0.19.1 소스에서 아래 수식에 사용하는 텍스트 함수 지원을 확인했습니다.

## 1. 언더스코어 컬럼명 → camelCase

원본이 A1에 있을 때 B1에 입력합니다.

```excel
=REPLACE(SUBSTITUTE(PROPER(SUBSTITUTE(A1,"_"," "))," ",""),1,1,LOWER(LEFT(A1,1)))
```

| A1 원본 | B1 결과 |
|---|---|
| USER_NAME | userName |
| CUST_NO | custNo |
| CRA_DTL_GRD_CD | craDtlGrdCd |
| user_name | userName |
| USER | user |

영문자로 시작하는 일반적인 언더스코어 컬럼명을 기준으로 합니다.
이미 카멜케이스인 값을 넣으면 내부 대문자가 소문자로 바뀔 수 있습니다.
예: userName → username.
숫자 뒤의 영문자는 PROPER 규칙에 따라 대문자로 바뀔 수 있습니다.
예: COL1_NAME → col1Name.

## 2. 수식이 처리되는 순서

USER_NAME을 예로 들면 다음과 같습니다.

| 단계 | 수식 | 결과 |
|---|---|---|
| 언더스코어를 공백으로 변경 | =SUBSTITUTE(A1,"_"," ") | USER NAME |
| 단어 첫 글자만 대문자로 변경 | =PROPER(SUBSTITUTE(A1,"_"," ")) | User Name |
| 공백 제거 | =SUBSTITUTE(PROPER(SUBSTITUTE(A1,"_"," "))," ","") | UserName |
| 첫 글자를 소문자로 교체 | 위의 최종 수식 | userName |

## 3. PascalCase 변환

Java 클래스명처럼 첫 글자도 대문자로 만들 때 사용합니다.

```excel
=SUBSTITUTE(PROPER(SUBSTITUTE(A1,"_"," "))," ","")
```

| A1 원본 | 결과 |
|---|---|
| USER_NAME | UserName |
| CRA_DTL_GRD_CD | CraDtlGrdCd |

## 4. 여러 행에 적용

1. A열에 원본 컬럼명을 한 행에 하나씩 붙여넣습니다.
2. B1에 camelCase 수식을 입력합니다.
3. B1을 복사해 B2:B100 등 필요한 범위에 붙여넣습니다.
4. 상대 참조가 적용되어 각 행의 A열 값을 변환합니다.
5. 변환 결과를 고정하려면 복사 후 선택하여 붙여넣기에서 값만 붙여넣습니다.

첫 행이 제목이면 원본을 A2부터 넣고, 수식의 A1을 모두 A2로 바꾸어 B2에 입력하세요.

## 5. 사용 함수

| 함수 | 용도 |
|---|---|
| SUBSTITUTE | 특정 문자열을 다른 문자열로 치환 |
| PROPER | 단어 첫 글자를 대문자로, 나머지는 소문자로 변환 |
| REPLACE | 지정한 위치의 문자를 교체 |
| LOWER | 소문자로 변환 |
| LEFT | 문자열 왼쪽에서 지정 개수만큼 추출 |

함수 지원 확인: [GridCraft v0.19.1 텍스트 함수 소스](https://github.com/storytold/gridcraft/blob/v0.19.1/crates/functions/src/text.rs)
