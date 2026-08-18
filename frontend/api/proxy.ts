import {
  proxyRenderRequest,
  type ProxyRequest,
  type ProxyResponse
} from '../server/renderProxy';

export default async function handler(request: ProxyRequest, response: ProxyResponse) {
  await proxyRenderRequest(request, response);
}
