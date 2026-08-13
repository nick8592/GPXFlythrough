/**
 * Type declarations for the CesiumJS global namespace.
 * CesiumJS is loaded via <script> tag (vite-plugin-cesium handles asset copying).
 * Only declare the subset we actually use.
 */
/* eslint-disable @typescript-eslint/no-extraneous-class */
declare namespace Cesium {
  class Viewer {
    constructor(
      container: HTMLElement | string,
      options?: ViewerOptions,
    );
    cesiumWidget: { creditContainer: HTMLElement };
    scene: Scene;
    camera: Camera;
    terrainProvider: unknown;
    entities: EntityCollection;
    destroy(): void;
  }

  interface ViewerOptions {
    terrainProvider?: unknown;
    animation?: boolean;
    timeline?: boolean;
    baseLayerPicker?: boolean;
    fullscreenButton?: boolean;
    vrButton?: boolean;
    geocoder?: boolean;
    homeButton?: boolean;
    infoBox?: boolean;
    sceneModePicker?: boolean;
    selectionIndicator?: boolean;
    navigationHelpButton?: boolean;
    requestRenderMode?: boolean;
    maximumRenderTimeChange?: number;
  }

  class Scene {
    skyBox: { show: boolean };
    skyAtmosphere: { show: boolean };
    backgroundColor: Color;
    globe: Globe;
    requestRender(): void;
  }

  class Globe {
    baseColor: Color;
    enableLighting: boolean;
    tilesLoaded: boolean;
  }

  class Camera {
    setView(options: CameraViewOptions): void;
  }

  interface CameraViewOptions {
    destination?: Cartesian3;
    orientation?: CameraOrientation;
  }

  interface CameraOrientation {
    heading?: number;
    pitch?: number;
    roll?: number;
    direction?: Cartesian3;
    up?: Cartesian3;
  }

  class EntityCollection {
    add(entity: Record<string, unknown>): Entity;
  }

  class Entity {
    position: Property;
  }

  class Property {}

  class CallbackProperty extends Property {
    constructor(
      callback: () => unknown,
      isConstant: boolean,
    );
  }

  class Cartesian3 {
    constructor(x?: number, y?: number, z?: number);
    static fromDegrees(
      longitude: number,
      latitude: number,
      height?: number,
    ): Cartesian3;
    static UNIT_Z: Cartesian3;
    static subtract(
      left: Cartesian3,
      right: Cartesian3,
      result: Cartesian3,
    ): Cartesian3;
  }

  class Cartesian2 {
    constructor(x?: number, y?: number);
  }

  class Color {
    static BLACK: Color;
    static WHITE: Color;
    static YELLOW: Color;
    static RED: Color;
    static BLUE: Color;
    static GREEN: Color;
    static CYAN: Color;
    static TRANSPARENT: Color;
    constructor(
      red: number,
      green: number,
      blue: number,
      alpha?: number,
    );
    withAlpha(alpha: number): Color;
    static fromCssColorString(css: string): Color;
  }

  class CesiumMath {
    static toRadians(degrees: number): number;
    static toDegrees(radians: number): number;
  }

  class EllipsoidTerrainProvider {}

  class PolylineGlowMaterialProperty {
    constructor(options: { glowPower: number; color: Color });
  }

  class LabelStyle {
    static FILL_AND_OUTLINE: number;
  }

  class VerticalOrigin {
    static BOTTOM: number;
    static CENTER: number;
  }

  class HorizontalOrigin {
    static CENTER: number;
  }

  class HeightReference {
    static NONE: number;
    static CLAMP_TO_GROUND: number;
    static RELATIVE_TO_GROUND: number;
  }

  class Ion {
    static defaultAccessToken: string;
  }

  function createWorldTerrainAsync(): Promise<unknown>;
}
