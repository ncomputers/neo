if ('serviceWorker' in navigator) {
  navigator.serviceWorker.addEventListener('message', (event) => {
    if (event.data?.type === 'UPDATE_READY') {
      const banner = document.createElement('div')
      banner.textContent = 'New version available '
      const button = document.createElement('button')
      button.textContent = 'Refresh'
      button.addEventListener('click', () => {
        navigator.serviceWorker.controller?.postMessage('SKIP_WAITING')
        window.location.reload()
      })
      banner.appendChild(button)
      banner.style.position = 'fixed'
      banner.style.bottom = '1rem'
      banner.style.right = '1rem'
      banner.style.padding = '0.5rem 1rem'
      banner.style.background = '#333'
      banner.style.color = '#fff'
      banner.style.borderRadius = '0.25rem'
      banner.style.zIndex = '1000'
      document.body.appendChild(banner)
    }
  })
}
