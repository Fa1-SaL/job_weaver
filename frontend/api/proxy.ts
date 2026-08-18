import {
  proxyRenderRequest,
  type ProxyRequest,
  type ProxyResponse
} from '../server/renderProxy.js';

export default async function handler(request: ProxyRequest, response: ProxyResponse) {
  await proxyRenderRequest(request, response);
}
