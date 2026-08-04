import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'

import BoundingBoxOverlay from '../safety/BoundingBoxOverlay.vue'

describe('BoundingBoxOverlay', () => {
  it('renders normalized bbox as percentage coordinates with readable confidence text', () => {
    const wrapper = mount(BoundingBoxOverlay, {
      props: {
        hazards: [
          {
            id: 'INC-1',
            hazard_type: 'no_helmet',
            hazard_name: '未佩戴安全帽',
            description: '未正确佩戴安全帽',
            confidence: 0.96,
            risk_level: 'high',
            bbox: [0.24, 0.18, 0.48, 0.86],
            review_required: true,
          },
        ],
      },
    })

    const box = wrapper.get('.detection-box')
    expect(box.attributes('style')).toContain('left: 24%')
    expect(box.attributes('style')).toContain('top: 18%')
    expect(box.text()).toContain('未佩戴安全帽')
    expect(box.text()).toContain('96%')
  })

  it('does not render a box for hazards without coordinates', () => {
    const wrapper = mount(BoundingBoxOverlay, {
      props: {
        hazards: [
          {
            id: 'INC-2',
            hazard_type: 'unknown',
            hazard_name: '现场隐患',
            description: '无定位框',
            confidence: 0.6,
            risk_level: 'medium',
            bbox: null,
            review_required: true,
          },
        ],
      },
    })

    expect(wrapper.findAll('.detection-box')).toHaveLength(0)
  })
})

