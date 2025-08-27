import { render, screen, fireEvent } from '@testing-library/react'
import OwnerOnboardingWizard from '../OwnerOnboardingWizard'

describe('OwnerOnboardingWizard', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('persists progress and resumes later', () => {
    const { unmount } = render(<OwnerOnboardingWizard />)
    fireEvent.change(screen.getByLabelText(/Brand Name/i), {
      target: { value: 'Cafe' },
    })
    fireEvent.click(screen.getByText(/Next/i))
    unmount()
    render(<OwnerOnboardingWizard />)
    expect(screen.getByText(/Step 2 of 6/i)).toBeInTheDocument()
    expect(screen.getByText(/Tables Count/i)).toBeInTheDocument()
  })

  it('shows launch checklist after completion', () => {
    render(<OwnerOnboardingWizard />)
    for (let i = 0; i < 6; i++) {
      fireEvent.click(screen.getByText(/Next/i))
    }
    const link = screen.getByText(/Launch checklist/i)
    expect(link).toBeInTheDocument()
    expect(link.getAttribute('href')).toBe('/help/owner_onboarding')
  })
})
