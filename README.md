# 근퇴 관리 웹사이트

## 실행
```sh
source ~/.zshrc
npm install
npm run dev
```

## 데이터 갱신
엑셀을 수정하면 아래 명령으로 JSON을 다시 생성할 수 있다.

```sh
npm run generate:data
```

`dev`, `build` 스크립트는 실행 전에 자동으로 데이터를 다시 생성한다.
