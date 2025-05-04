설명:

위 코드는 프런트엔드 코드의 유닛 및 통합 테스트를 위한 예시입니다. Jest와 React Testing Library, 그리고 Fetch API Mocking을 사용합니다.

테스트 환경 설정:

package.json: jest, @testing-library/react, @testing-library/jest-dom, babel-jest, @babel/core, @babel/preset-env, @babel/preset-react, identity-obj-proxy, jest-fetch-mock 등 필요한 라이브러리를 devDependencies에 추가합니다.
jest.config.js: Jest의 기본 설정 파일입니다. 브라우저 환경 시뮬레이션을 위한 testEnvironment: 'jsdom', 테스트 실행 전 추가 설정을 위한 setupFilesAfterEnv, CSS나 이미지를 Mocking하기 위한 moduleNameMapper, JSX 코드를 JS로 변환하기 위한 transform 등을 설정합니다.
babel.config.js: Jest에서 React JSX 구문과 최신 JavaScript 문법을 이해하도록 Babel 설정을 정의합니다.
setupTests.js: 각 테스트 파일이 실행되기 전에 자동으로 임포트되어 실행되는 파일입니다. 여기서는 @testing-library/jest-dom를 임포트하여 DOM 관련 추가 Jest matcher를 사용 가능하게 하고, jest-fetch-mock를 설정하여 Workspace API 호출을 가로채 Mock 응답을 반환할 수 있도록 합니다.
__mocks__/fileMock.js: CSS, 이미지 등 웹팩이 처리하는 정적 자산 파일을 Mocking하기 위한 간단한 파일입니다.
컴포넌트 테스트 (FileUploader.test.js, TaskItem.test.js):

@testing-library/react의 render 함수를 사용하여 React 컴포넌트를 메모리상의 가상 DOM에 렌더링합니다.
screen 객체를 사용하여 렌더링된 컴포넌트에서 특정 텍스트, 역할(role), 레이블 등으로 요소를 찾습니다 (getByRole, getByText, getByLabelText, queryByRole). queryByRole은 요소가 없으면 null을 반환하므로 부재 여부 테스트에 유용합니다.
@testing-library/jest-dom의 Matchers(예: toBeInTheDocument, toBeDisabled)를 사용하여 요소의 존재 여부, 상태 등을 검증합니다.
fireEvent를 사용하여 사용자의 이벤트를 시뮬레이션합니다 (예: 버튼 클릭 fireEvent.click, 파일 입력 변경 fireEvent.change).
jest.fn()을 사용하여 컴포넌트의 props로 전달되는 콜백 함수(예: onFileSelect, onUpload, onViewResults)를 Mocking하고, 이 Mock 함수가 예상대로 호출되었는지, 어떤 인자로 호출되었는지(toHaveBeenCalledTimes, toHaveBeenCalledWith) 검증합니다.
API 서비스 테스트 (apiService.test.js):

jest-fetch-mock 라이브러리를 사용하여 브라우저의 Workspace API 호출을 Mocking합니다. 실제 네트워크 요청 없이 테스트 코드에서 Mock 응답을 제어할 수 있습니다.
WorkspaceMock.mockResponseOnce(JSON.stringify(mockResponseData), { status: 200 }); 와 같이 특정 URL로 Workspace가 호출될 때 반환할 Mock 응답 데이터와 HTTP 상태 코드를 설정합니다.
WorkspaceMock.mockResponseOnce(errorBody, { status: 400 }); 또는 WorkspaceMock.mockResponseOnce(errorMessage, { status: 500 }); 와 같이 오류 응답을 설정하여 실패 시나리오를 테스트합니다.
expect(fetch).toHaveBeenCalledTimes(1) 또는 expect(fetch).toHaveBeenCalledWith(...)를 사용하여 Workspace 함수가 예상대로 호출되었는지, 어떤 URL과 옵션으로 호출되었는지 검증합니다. expect.stringContaining을 사용하여 URL의 일부만 검증할 수 있습니다.
expect(responseOptions.method).toBe('POST')와 같이 요청 옵션을 검증합니다. 파일 업로드 테스트에서는 expect(responseOptions.body).toBeInstanceOf(FormData)로 FormData 객체가 전달되었는지 확인합니다.
함수가 성공 시 예상된 파싱된 데이터를 반환하는지(expect(result).toEqual(mockResponseData)) 확인하고, 실패 시 예상된 오류를 발생시키는지(expect(...).rejects.toThrow(...)) 검증합니다.
파일 업로드 진행 상태(onProgress 콜백) 테스트는 axios와 같은 라이브러리를 사용해야 더 정확한 Mocking이 가능합니다. Workspace의 기본 구현에서는 Mocking이 제한적입니다.


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

