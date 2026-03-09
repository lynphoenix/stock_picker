import '@testing-library/jest-dom'

// Mock window.matchMedia for Ant Design
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

// Mock ResizeObserver
class MockResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
global.ResizeObserver = MockResizeObserver

// Mock HTMLCanvasElement getContext for ECharts
HTMLCanvasElement.prototype.getContext = vi.fn()
HTMLCanvasElement.prototype.toDataURL = vi.fn()
HTMLCanvasElement.prototype.toBlob = vi.fn()

// Mock ECharts - use require for JSX
vi.mock('echarts-for-react', () => ({
  default: () => '<div data-testid="chart">Chart</div>',
}))
