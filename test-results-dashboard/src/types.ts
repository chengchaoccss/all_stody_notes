export type TestStatus = 'pass' | 'fail';

export type ExpectedResultType = 'image' | 'text';

export interface ExpectedResult {
  type: ExpectedResultType;
  /** URL when type is 'image' */
  imageUrl?: string;
  /** Natural language description when type is 'text' */
  description?: string;
}

export interface TestRecord {
  id: string;
  /** Original test screenshot URL */
  screenshotUrl: string;
  /** Expected result - can be image or text description */
  expectedResult: ExpectedResult;
  /** AI analysis result text */
  aiAnalysis: string;
  /** Test conclusion: pass or fail */
  status: TestStatus;
  /** Test timestamp ISO string */
  timestamp: string;
}
