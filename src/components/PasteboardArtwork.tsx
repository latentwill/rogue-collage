/** Four independent SVG crop views share one cached source image. */
export function PasteboardArtwork(){return <div className="pasteboard-artwork" aria-hidden="true">{['top-left','top-right','bottom-left','bottom-right'].map(corner=><img key={corner} className={corner} src={`/brand/pasteboard-corners.svg#${corner}`} alt="" draggable={false}/>)}</div>}
