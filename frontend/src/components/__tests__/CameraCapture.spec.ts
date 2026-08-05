import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

import CameraCapture from '@/components/capture/CameraCapture.vue'

const track = { stop: vi.fn() }
const fakeStream = { getTracks: () => [track] } as unknown as MediaStream

function stubMediaDevices(getUserMedia: () => Promise<MediaStream> = () => Promise.resolve(fakeStream)): void {
  Object.defineProperty(navigator, 'mediaDevices', {
    configurable: true,
    value: {
      getUserMedia: vi.fn(getUserMedia),
      enumerateDevices: vi.fn().mockResolvedValue([]),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    },
  })
}

function stubCanvas(): void {
  const drawImage = vi.fn()
  HTMLCanvasElement.prototype.getContext = vi.fn(() => ({ drawImage })) as unknown as typeof HTMLCanvasElement.prototype.getContext
  HTMLCanvasElement.prototype.toBlob = vi.fn((callback: BlobCallback) => {
    callback(new Blob(['x'], { type: 'image/jpeg' }))
  }) as unknown as typeof HTMLCanvasElement.prototype.toBlob
}

function overlay(): Element | null {
  return document.body.querySelector('.capture-overlay')
}

function overlayButton(text: string): HTMLButtonElement {
  const buttons = document.body.querySelectorAll<HTMLButtonElement>('.capture-dialog button')
  const found = Array.from(buttons).find((button) => button.textContent?.includes(text))
  if (!found) throw new Error(`未找到按钮：${text}`)
  return found
}

function prepareVideo(): HTMLVideoElement {
  const video = document.body.querySelector<HTMLVideoElement>('.capture-stage video')
  if (!video) throw new Error('摄像头预览 video 未渲染')
  Object.defineProperty(video, 'videoWidth', { configurable: true, value: 1280 })
  Object.defineProperty(video, 'videoHeight', { configurable: true, value: 720 })
  return video
}

describe('CameraCapture', () => {
  beforeEach(() => {
    stubMediaDevices()
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
    delete (navigator as unknown as { mediaDevices?: unknown }).mediaDevices
    document.body.innerHTML = ''
  })

  it('渲染「相机拍照」触发按钮，未打开时不请求摄像头', () => {
    const wrapper = mount(CameraCapture)
    expect(wrapper.find('button.capture-trigger').text()).toContain('相机拍照')
    expect(navigator.mediaDevices.getUserMedia).not.toHaveBeenCalled()
    expect(overlay()).toBeNull()
  })

  it('点击触发按钮后请求摄像头，拍摄一帧并 emit JPEG File', async () => {
    stubCanvas()
    const wrapper = mount(CameraCapture)

    await wrapper.find('button.capture-trigger').trigger('click')
    await flushPromises()

    expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalledTimes(1)
    expect(overlay()).not.toBeNull()

    prepareVideo()
    await overlayButton('拍摄').click()
    await flushPromises()

    const emitted = wrapper.emitted('captured')
    expect(emitted).toBeDefined()
    const file = emitted![0]![0] as File
    expect(file).toBeInstanceOf(File)
    expect(file.type).toBe('image/jpeg')
    expect(file.name).toMatch(/^camera-\d+\.jpg$/)
    // 拍摄成功后自动关闭弹窗并停止摄像头
    expect(overlay()).toBeNull()
    expect(track.stop).toHaveBeenCalled()
  })

  it('权限被拒绝时展示中文原因并禁用拍摄按钮', async () => {
    stubMediaDevices(() => Promise.reject(new DOMException('denied', 'NotAllowedError')))
    const wrapper = mount(CameraCapture)

    await wrapper.find('button.capture-trigger').trigger('click')
    await flushPromises()

    expect(overlay()?.textContent).toContain('摄像头权限被拒绝')
    expect(overlayButton('拍摄').disabled).toBe(true)
  })

  it('取消时停止摄像头并关闭弹窗', async () => {
    const wrapper = mount(CameraCapture)
    await wrapper.find('button.capture-trigger').trigger('click')
    await flushPromises()
    expect(overlay()).not.toBeNull()

    await overlayButton('取消').click()
    await flushPromises()

    expect(overlay()).toBeNull()
    expect(track.stop).toHaveBeenCalled()
  })
})
