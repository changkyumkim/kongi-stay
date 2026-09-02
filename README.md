# 콩이스테이 (kongi-stay)

우리 개가 갈 수 있는 호텔을 체중·체고로 갈라서 보여주는 사이트.

## 호텔을 추가하려면

`hotels.json` 하나만 고치면 된다. 저장하고 푸시하면 사이트가 자동으로 다시 구워진다.

다른 파일은 안 만져도 된다.

## 값 설명

| 이름 | 뜻 |
|---|---|
| `agoda_hid` | 아고다 호텔 페이지에서 `Ctrl+U` → `Ctrl+F` → `hotelId` |
| `max_weight_kg` | 받아주는 최대 몸무게. **비면 걸러지지 않는다** |
| `max_height_cm` | 받아주는 최대 체고 |
| `fee_unit` | `1박당` / `1박1마리` / `1회` / `무료` |
| `source_url` | 규정을 확인한 페이지 |
| `checked_on` | 확인한 날짜 |

**모르는 값은 `null`.** 추측해서 넣으면 사람이 개를 데려갔다가 못 들어간다.

## 아고다 값 (GitHub Secrets)

`Settings → Secrets and variables → Actions` 에 세 개:

- `AGODA_SITE_ID`
- `AGODA_API_KEY`
- `AGODA_API_URL`

없어도 사이트는 만들어진다. 사진·평점만 안 붙는다.

## 손으로 굽기

```
pip install requests python-dotenv
python build.py
```
