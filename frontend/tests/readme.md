실행 방법:

프런트엔드 프로젝트의 루트 디렉토리(frontend/)에서 필요한 라이브러리를 설치합니다: npm install --save-dev jest @testing-library/react @testing-library/jest-dom babel-jest @babel/core @babel/preset-env @babel/preset-react identity-obj-proxy jest-fetch-mock httpx (또는 yarn add --dev ...)
위 예시의 설정 파일(jest.config.js, babel.config.js, setupTests.js, __mocks__/fileMock.js)을 프로젝트 구조에 맞게 생성하거나 수정합니다.
테스트 파일(.test.js 또는 .test.jsx)을 tests/__tests__/ 디렉토리 구조에 맞게 배치합니다.
package.json 파일의 scripts 섹션에 Jest 실행 명령을 추가합니다.
JSON

"scripts": {
  "test": "jest",
  "test:watch": "jest --watch",
  "test:coverage": "jest --coverage"
}
터미널에서 npm test (또는 yarn test) 명령을 실행하여 테스트를 수행합니다.
이 테스트 코드들은 프런트엔드 컴포넌트의 렌더링 및 사용자 인터랙션, 그리고 백엔드 API 호출 로직이 올바르게 작동하는지 검증하는 기본적인 방법을 보여줍니다. 나머지 프런트엔드 컴포넌트들과 더 복잡한 상호작용 및 상태 변화 시나리오에 대해서도 이러한 방식으로 테스트를 확장할 수 있습니다.

