/**
 * Insight Engine n8n 노드 (F7-07)
 *
 * n8n 워크플로우에서 Insight Engine API를 호출하여
 * YouTube 영상에서 AI 콘텐츠를 생성합니다.
 *
 * 설치: n8n-node-dev 또는 커스텀 노드 디렉토리에 배치
 */

import {
  IExecuteFunctions,
  INodeExecutionData,
  INodeType,
  INodeTypeDescription,
  NodeOperationError,
} from 'n8n-workflow';

export class InsightEngine implements INodeType {
  description: INodeTypeDescription = {
    displayName: 'Insight Engine',
    name: 'insightEngine',
    icon: 'file:insightEngine.svg',
    group: ['transform'],
    version: 1,
    subtitle: '={{$parameter["operation"]}}',
    description: 'YouTube 영상 URL로 AI 콘텐츠를 생성합니다.',
    defaults: {
      name: 'Insight Engine',
    },
    inputs: ['main'],
    outputs: ['main'],
    credentials: [
      {
        name: 'insightEngineApi',
        required: false,
        displayOptions: {
          show: { operation: ['generate', 'publish'] },
        },
      },
    ],
    properties: [
      {
        displayName: '서버 URL',
        name: 'serverUrl',
        type: 'string',
        default: 'http://localhost:5001',
        description: 'Insight Engine 서버 URL',
        required: true,
      },
      {
        displayName: '작업',
        name: 'operation',
        type: 'options',
        noDataExpression: true,
        options: [
          {
            name: '콘텐츠 생성',
            value: 'generate',
            description: 'YouTube URL로 AI 콘텐츠를 생성합니다.',
            action: 'Generate content from YouTube URL',
          },
          {
            name: '플러그인 목록',
            value: 'listPlugins',
            description: '사용 가능한 MCP 플러그인 목록을 가져옵니다.',
            action: 'List available MCP plugins',
          },
          {
            name: '콘텐츠 발행',
            value: 'publish',
            description: 'MCP 플러그인으로 콘텐츠를 발행합니다.',
            action: 'Publish content via MCP plugin',
          },
        ],
        default: 'generate',
      },

      // generate 작업 파라미터
      {
        displayName: 'YouTube URL',
        name: 'youtubeUrl',
        type: 'string',
        default: '',
        required: true,
        displayOptions: { show: { operation: ['generate'] } },
        description: '콘텐츠를 생성할 YouTube 영상 URL',
      },
      {
        displayName: '스타일',
        name: 'styleId',
        type: 'options',
        displayOptions: { show: { operation: ['generate'] } },
        options: [
          { name: '블로그 SEO', value: 'blog_seo' },
          { name: '요약', value: 'summary' },
          { name: '튜토리얼', value: 'tutorial' },
          { name: 'Q&A', value: 'qna' },
          { name: 'SNS 포스트', value: 'sns_post' },
          { name: '뉴스레터', value: 'newsletter' },
        ],
        default: 'blog_seo',
      },
      {
        displayName: '언어',
        name: 'language',
        type: 'options',
        displayOptions: { show: { operation: ['generate'] } },
        options: [
          { name: '한국어', value: 'ko' },
          { name: 'English', value: 'en' },
          { name: '日本語', value: 'ja' },
        ],
        default: 'ko',
      },
      {
        displayName: '길이',
        name: 'length',
        type: 'options',
        displayOptions: { show: { operation: ['generate'] } },
        options: [
          { name: '짧게', value: 'short' },
          { name: '보통', value: 'medium' },
          { name: '길게', value: 'long' },
        ],
        default: 'medium',
      },

      // publish 작업 파라미터
      {
        displayName: '플러그인 ID',
        name: 'pluginId',
        type: 'string',
        default: '',
        required: true,
        displayOptions: { show: { operation: ['publish'] } },
        description: '사용할 MCP 플러그인 ID',
      },
      {
        displayName: '제목',
        name: 'title',
        type: 'string',
        default: '',
        displayOptions: { show: { operation: ['publish'] } },
      },
      {
        displayName: '콘텐츠',
        name: 'content',
        type: 'string',
        typeOptions: { rows: 4 },
        default: '',
        displayOptions: { show: { operation: ['publish'] } },
      },
    ],
  };

  async execute(this: IExecuteFunctions): Promise<INodeExecutionData[][]> {
    const items = this.getInputData();
    const returnData: INodeExecutionData[] = [];

    for (let i = 0; i < items.length; i++) {
      const serverUrl = (this.getNodeParameter('serverUrl', i) as string).replace(/\/$/, '');
      const operation = this.getNodeParameter('operation', i) as string;

      try {
        let result: unknown;

        if (operation === 'generate') {
          const youtubeUrl = this.getNodeParameter('youtubeUrl', i) as string;
          const styleId = this.getNodeParameter('styleId', i) as string;
          const language = this.getNodeParameter('language', i) as string;
          const length = this.getNodeParameter('length', i) as string;

          const response = await this.helpers.request({
            method: 'POST',
            url: `${serverUrl}/generate`,
            body: {
              urls: [youtubeUrl],
              style_id: styleId,
              modifiers: { language, length },
            },
            json: true,
          });
          result = response;

        } else if (operation === 'listPlugins') {
          const response = await this.helpers.request({
            method: 'GET',
            url: `${serverUrl}/api/mcp/plugins`,
            json: true,
          });
          result = response;

        } else if (operation === 'publish') {
          const pluginId = this.getNodeParameter('pluginId', i) as string;
          const title = this.getNodeParameter('title', i) as string;
          const content = this.getNodeParameter('content', i) as string;

          const response = await this.helpers.request({
            method: 'POST',
            url: `${serverUrl}/api/mcp/publish`,
            body: { plugin_id: pluginId, title, content },
            json: true,
          });
          result = response;
        }

        returnData.push({ json: result as Record<string, unknown> });

      } catch (error) {
        if (this.continueOnFail()) {
          returnData.push({ json: { error: (error as Error).message } });
          continue;
        }
        throw new NodeOperationError(this.getNode(), error as Error, { itemIndex: i });
      }
    }

    return [returnData];
  }
}
